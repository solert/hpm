from PySide2.QtCore import QObject, Signal
from constants import STANDARD_STYLE_DICT, ERROR_STYLE_DICT
from . import utils


# Classe pour exécuter des fonctions dans un thread à part, et ainsi éviter le freezing de la GUI
class Worker(QObject):
    update_progressbar = Signal(int)
    update_label = Signal(str, dict)
    update_log_list_widget = Signal(str, dict)
    finished = Signal()

    def __init__(self, ui):
        super().__init__()
        self.ui = ui

    # Gestion de l'interruption du pricing par l'utilisateur
    def exit_if_interruption_requested(self):
        if self.ui.thread.isInterruptionRequested():
            raise KeyboardInterrupt("Programme interrompu par l'utilisateur")

    # Emission des signals
    def emit_signals(
        self,
        label_message=None,
        log_list_widget_message=None,
        style_dict=STANDARD_STYLE_DICT,
        progressbar_value=None,
        finished=False,
    ):
        if label_message is not None:
            self.update_label.emit(label_message, style_dict)
        if log_list_widget_message is not None:
            self.update_log_list_widget.emit(log_list_widget_message, style_dict)
        if progressbar_value is not None:
            self.update_progressbar.emit(progressbar_value)
        if finished:
            self.finished.emit()

    def run_pricing(self):
        try:
            # Initialisation des widgets
            beg_message = "Lancement du pricing"
            self.emit_signals(beg_message, beg_message, progressbar_value=0)

            # Cas où aucune ligne n'a été créée dans la section "Paramétrage" (aucun hôtel à pricer)
            hotels_to_price_nb = self.ui.param_widget_vlayout.count() - 1
            if not hotels_to_price_nb:
                error_message = "Erreur : Veuillez effectuer au moins un paramétrage"
                self.emit_signals(error_message, error_message, ERROR_STYLE_DICT, finished=True)
                return

            # Récupération de la méthode de pricing choisie
            if self.ui.no_edit_option.isChecked():
                method = "no-edit"
            elif self.ui.edit_option.isChecked():
                method = "edit"
            else:
                error_message = "Erreur : Veuillez sélectionner une méthode de pricing"
                self.emit_signals(error_message, error_message, ERROR_STYLE_DICT, finished=True)
                return

            information_list = []
            # On calcule le nombre total de jours à pricer afin de calculer le pourcentage de progression
            self.date_idx = 0
            self.total_nb_days = 0
            for i in range(hotels_to_price_nb):
                hlayout = self.ui.param_widget_vlayout.itemAt(i)
                # On stocke toutes les informations de l'hôtel
                username = hlayout.itemAt(0).widget().currentText()
                password = self.ui.df_ids.loc[self.ui.df_ids["username"] == username, "password"].iloc[0]
                hotel_name = hlayout.itemAt(1).widget().currentText()
                hotel_is_alone = (
                    True
                    if self.ui.df_ids.loc[
                        (self.ui.df_ids["username"] == username) & (self.ui.df_ids["hotel_name"] == hotel_name),
                        "is_alone",
                    ].item()
                    == "yes"
                    else False
                )
                room_type = self.ui.df_ids.loc[
                    (self.ui.df_ids["username"] == username) & (self.ui.df_ids["hotel_name"] == hotel_name), "room_type"
                ].item()
                price_type = self.ui.df_ids.loc[
                    (self.ui.df_ids["username"] == username) & (self.ui.df_ids["hotel_name"] == hotel_name),
                    "price_type",
                ].item()
                beg_date = hlayout.itemAt(2).widget().date().toPython()
                end_date = hlayout.itemAt(3).widget().date().toPython()
                prices_path = self.ui.df_ids.loc[
                    (self.ui.df_ids["username"] == username) & (self.ui.df_ids["hotel_name"] == hotel_name), "path"
                ].item()

                information_list.append(
                    (
                        username,
                        password,
                        hotel_name,
                        hotel_is_alone,
                        room_type,
                        price_type,
                        beg_date,
                        end_date,
                        prices_path,
                    )
                )
                self.total_nb_days += (end_date - beg_date).days + 1

            # Préparation du driver
            if not self.ui.bot.driver_has_been_prepared:
                message = "Installation du driver"
                self.emit_signals(message, message)
                self.ui.bot.prepare_driver()

            # Récupération de la liste des onglets/fenêtres du navigateur pour s'assurer que ce dernier est bien ouvert
            try:
                tabs = self.ui.bot.driver.window_handles

                # Récupération de l'onglet ciblé par le driver pour s'assurer que cet onglet n'a pas été fermé par l'utilisateur
                try:
                    self.ui.bot.driver.current_window_handle

                # Si l'onglet ciblé a été fermé, on ouvre un nouvel onglet et on le cible
                except:
                    # On ne peut ouvrir un nouvel onglet qu'à partir d'un onglet ouvert ciblé, donc on cible le premier onglet de la liste des onglets actuellement ouverts
                    self.ui.bot.driver.switch_to.window(tabs[0])

                    # Ne fonctionne qu'à partir de selenium 4.
                    # Sous selenium < 4, il faudrait utiliser : self.ui.bot.driver.execute_script("window.open('');") puis new_tabs = self.ui.bot.driver.window_handles pour
                    # switch vers le seul onglet dans new_tabs qui n'est pas dans tabs
                    self.ui.bot.driver.switch_to.new_window("tab")

            # Si le navigateur n'a jamais été ouvert (i.e. l'attribut driver n'existe pas) ou a été fermé par l'utilisateur, on ouvre
            # une nouvelle fenêtre de navigateur (et donc on crée une nouvelle instance de driver)
            # NB : si l'erreur est différente, on est plutôt confiant sur le fait qu'une nouvelle erreur interrompra le programme
            except Exception:
                message = "Ouverture du navigateur"
                self.emit_signals(message, message)
                self.ui.bot.create_driver()

            # On aurait pu ne faire qu'une boucle mais en faire 2 permet de voir s'il y a un problème dans la récupération des inputs avant même de lancer le pricing
            for (
                username,
                password,
                hotel_name,
                hotel_is_alone,
                room_type,
                price_type,
                beg_date,
                end_date,
                prices_path,
            ) in information_list:
                self.exit_if_interruption_requested()
                self.ui.bot.go_to_home_page()
                self.ui.bot.login(username, password, create_cookie=True, worker=self)
                df_prices = utils.fetch_prices(prices_path, beg_date, end_date, hotel_name, worker=self)
                self.ui.bot.check_prices(
                    hotel_is_alone,
                    room_type,
                    price_type,
                    beg_date,
                    end_date,
                    df_prices,
                    method,
                    hotel_name,
                    worker=self,
                )

            success_message = "Pricing terminé"
            self.emit_signals(success_message, success_message, finished=True)

        except (KeyboardInterrupt, Exception) as e:
            label_error_message = "Erreur : Voir registre"
            log_list_widget_error_message = "Erreur : " + str(e)
            self.emit_signals(label_error_message, log_list_widget_error_message, ERROR_STYLE_DICT, -1, True)
            return
