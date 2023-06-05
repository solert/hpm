import os
import datetime as dt
import pandas as pd
from PySide2.QtWidgets import (
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QScrollArea,
    QGroupBox,
    QRadioButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFrame,
)  # QAbstractItemView, QCheckBox
from PySide2.QtCore import Qt, QThread
from PySide2.QtGui import QColor  # QFont, QTextCharFormat
from . import worker
from . import customized_widgets as cw
from constants import ROOT_PATH, SETTINGS_DICT, APP_NAME, Version


class Hpm(QWidget):
    def __init__(self, bot=None, desktop_size=None, version: Version = Version.FREE) -> None:
        super().__init__()
        self.init_window(desktop_size)

        # Main settings
        self.bot = bot
        self.today = dt.date.today()
        self.load_settings()
        self.df_ids = pd.read_excel(self.ids_path, keep_default_na=False)
        self.update_lists()
        self.handle_version(version)

        self.build_widgets()

    def build_widgets(self) -> None:
        self.main_layout = QVBoxLayout(self)  # Window main layout
        self.tab_widget = QTabWidget()

        # PROGRAM tab
        self.program_widget = QWidget()

        # Création d'un vertical layout qui contiendra toutes les groupboxes
        self.program_vlayout = QVBoxLayout(self.program_widget)
        self.program_vlayout.setAlignment(Qt.AlignTop)

        ## Section 'Paramétrage'
        self.param_groupbox = QGroupBox("Paramétrage")
        self.param_groupbox_vlayout = QVBoxLayout()

        # Création d'une scrollarea qui agira sur un QWidget contenant les lignes du Manager (une scroll area ne peut a priori pas englober un layout, d'où la création de ce QWidget)
        self.param_scroll_area = QScrollArea()
        self.param_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.param_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.param_scroll_area.setWidgetResizable(True)
        self.param_vscroll_bar = self.param_scroll_area.verticalScrollBar()
        self.param_widget = QWidget()

        # Scroll automatique vers la dernière ligne ajoutée
        self.param_vscroll_bar.rangeChanged.connect(
            lambda *args: self.param_vscroll_bar.setValue(self.param_vscroll_bar.maximum())
        )

        # Création d'un vertical layout qui appartiendra au param_widget, et qui contiendra chaque ligne du Manager sous forme d'horizontal layout
        self.param_widget_vlayout = QVBoxLayout()
        self.param_widget_vlayout.setAlignment(Qt.AlignTop)

        # Création d'un horizontal layout qui contiendra les boutons 'Ajouter' et 'Effacer tout'
        self.param_last_hlayout = QHBoxLayout()
        self.param_last_hlayout.setAlignment(Qt.AlignLeft)

        self.add_hotel_button = cw.CustomPushButton("Ajouter", self.add_hotel, "Ajouter un hôtel")
        self.clear_button = cw.CustomPushButton("Effacer tout", self.clear, "Effacer toutes les lignes")

        ## Section 'Pricing'
        self.pricing_groupbox = QGroupBox("Pricing")
        self.pricing_hlayout = QHBoxLayout()
        self.pricing_hlayout.setAlignment(Qt.AlignLeft)

        # Création de boutons pour choisir la méthode d'exécution du programme
        self.no_edit_option = QRadioButton("Vérifier")
        self.edit_option = QRadioButton("Modifier")
        self.edit_option.setChecked(True)  # Bouton "Modifier" sélectionné par défaut

        # Création du bouton 'Lancer'
        self.run_pricing_button = cw.CustomPushButton("Lancer", self.run_pricing, "Lancer le pricing")

        ## Section 'Registre'
        # Création d'une groupbox 'Registre' qui stocke et affiche toutes les étapes importantes
        self.log_groupbox = QGroupBox("Registre")
        self.log_vlayout = QVBoxLayout()
        self.log_list_widget = QListWidget()
        self.log_vscroll_bar = self.log_list_widget.verticalScrollBar()  # QListWidget contient une scroll bar par défaut

        # Scroll automatique vers le dernier item ajouté
        self.log_vscroll_bar.rangeChanged.connect(
            lambda *args: self.log_vscroll_bar.setValue(self.log_vscroll_bar.maximum())
        )

        # --- ONGLET PARAMETRES D-EDGE --- #
        # Création de l'onglet Paramètres
        self.dedge_settings_widget = QWidget()
        self.dedge_settings_vlayout = QVBoxLayout(self.dedge_settings_widget)

        # Création d'un tableau à partir de self.df_ids
        self.table_ids = cw.CustomTable(
            df=self.df_ids,
            add_icon_path=self.add_icon_path,
            remove_icon_path=self.remove_icon_path,
        )

        # Création d'un delegate personnalisé pour la colonne "path" : editor -> QToolButton + QLineEdit
        path_delegate = cw.PathSelectionDelegate(self, self.folder_icon_path)
        path_column_index = self.table_ids.columns.index("path")
        self.table_ids.setItemDelegateForColumn(path_column_index, path_delegate)

        # Création d'un delegate personnalisé pour la colonne "is_alone" : editor -> QComboBox
        is_alone_delegate = cw.ComboBoxDelegate(self, header="Sélectionner", items=["yes", "no"])
        is_alone_column_index = self.table_ids.columns.index("is_alone")
        self.table_ids.setItemDelegateForColumn(is_alone_column_index, is_alone_delegate)

        # Boutons Ajouter, Vider, Rétablir et Sauvegarder
        self.dedge_settings_hlayout = QHBoxLayout()
        self.add_id_button = cw.CustomPushButton("Ajouter", self.table_ids.add_row, "Ajouter un id")
        self.empty_table_ids_button = cw.CustomPushButton(
            "Vider", lambda *args: self.table_ids.setRowCount(0), "Vider le tableau"
        )
        self.restore_table_ids_button = cw.CustomPushButton(
            "Rétablir", lambda *args: self.table_ids.fill(self.df_ids), "Annuler les changements effectués"
        )
        self.save_table_ids_button = cw.CustomPushButton(
            "Sauvegarder", self.save_table_ids, "Sauvegarder les changements effectués"
        )

        self.dedge_settings_hlayout.setAlignment(Qt.AlignLeft)

        # Mise en relief du bouton "Sauvegarder" à chaque modification du tableau (et réinitialisation du bouton après son click)
        table_edited_func = lambda *args: self.save_table_ids_button.setStyleSheet(
            "QPushButton {background-color: darkCyan;}"
        )
        self.table_ids.itemChanged.connect(table_edited_func)
        self.table_ids.model().rowsInserted.connect(table_edited_func)
        self.table_ids.model().rowsRemoved.connect(table_edited_func)

        table_not_edited_func = lambda *args: self.save_table_ids_button.setStyleSheet("")
        self.restore_table_ids_button.clicked.connect(table_not_edited_func)
        self.save_table_ids_button.clicked.connect(table_not_edited_func)

        # --- Settings tab --- #
        self.settings_widget = QWidget()
        settings_vlayout = QVBoxLayout(self.settings_widget)
        settings_vlayout.setAlignment(Qt.AlignTop)

        # Type de sélection du chemin dans la colonne path du tableau (folder vs file)
        path_selection_hlayout = QHBoxLayout()
        path_selection_hlayout.setAlignment(Qt.AlignLeft)
        path_selection_label = QLabel("Type de sélection des chemins:")
        folder_selection_option = QRadioButton("Dossier")
        folder_selection_option.clicked.connect(lambda *args: path_delegate.set_path_selection_type("folder"))
        file_selection_option = QRadioButton("Fichier")
        file_selection_option.clicked.connect(lambda *args: path_delegate.set_path_selection_type("file"))
        # Choix de 'file' par défaut
        file_selection_option.setChecked(True)
        path_delegate.set_path_selection_type("file")

        # Mise en page (layouts et widgets)
        self.main_layout.addWidget(self.tab_widget)

        self.tab_widget.addTab(self.program_widget, "Programme")

        self.program_vlayout.addWidget(self.param_groupbox)
        self.param_groupbox.setLayout(self.param_groupbox_vlayout)
        self.param_groupbox_vlayout.addWidget(self.param_scroll_area)
        self.param_scroll_area.setWidget(self.param_widget)
        self.param_widget.setLayout(self.param_widget_vlayout)
        self.param_widget_vlayout.addLayout(self.param_last_hlayout)
        self.param_last_hlayout.addWidget(self.add_hotel_button)
        self.param_last_hlayout.addWidget(self.clear_button)

        self.program_vlayout.addWidget(self.pricing_groupbox)
        self.pricing_groupbox.setLayout(self.pricing_hlayout)
        self.pricing_hlayout.addWidget(self.no_edit_option)
        self.pricing_hlayout.addWidget(self.edit_option)
        self.pricing_hlayout.addWidget(self.run_pricing_button)

        self.program_vlayout.addWidget(self.log_groupbox)
        self.log_groupbox.setLayout(self.log_vlayout)
        self.log_vlayout.addWidget(self.log_list_widget)

        self.tab_widget.addTab(self.dedge_settings_widget, "Paramètres D-Edge")

        self.dedge_settings_vlayout.addWidget(self.table_ids)
        self.dedge_settings_vlayout.addLayout(self.dedge_settings_hlayout)
        for widget in [
            self.add_id_button,
            self.empty_table_ids_button,
            self.restore_table_ids_button,
            self.save_table_ids_button,
        ]:
            self.dedge_settings_hlayout.addWidget(widget)

        if self.settings_icon_path:
            settings_icon = cw.build_icon_from_path(self.settings_icon_path)
            self.tab_widget.addTab(self.settings_widget, settings_icon, None)
        else:
            self.tab_widget.addTab(self.settings_widget, "Paramètres")
        settings_vlayout.addLayout(path_selection_hlayout)
        path_selection_hlayout.addWidget(path_selection_label)
        path_selection_hlayout.addWidget(folder_selection_option)
        path_selection_hlayout.addWidget(file_selection_option)

        self.show()  # Display windows

    def init_window(self, desktop_size=None) -> None:
        self.setWindowTitle(APP_NAME)
        if desktop_size is not None:
            self.setGeometry(0, 0, desktop_size.width() // 2, desktop_size.height() - 32)
        else:
            self.showMaximized()
        # Forced to do move(0, 0) because 'setGeometry' does an offset from (0,0) pos (as the 'set_window_position(0,0)' of Selenium's driver)
        self.move(0, 0)

    def load_settings(self):
        self.ids_path = os.path.join(ROOT_PATH, SETTINGS_DICT["ids_path"])
        self.add_icon_path = os.path.join(ROOT_PATH, SETTINGS_DICT["add_icon_path"])
        self.remove_icon_path = os.path.join(ROOT_PATH, SETTINGS_DICT["remove_icon_path"])
        self.folder_icon_path = os.path.join(ROOT_PATH, SETTINGS_DICT["folder_icon_path"])
        self.settings_icon_path = os.path.join(ROOT_PATH, SETTINGS_DICT["settings_icon_path"])

    def handle_version(self, version: Version) -> None:
        if version == Version.FREE:
            self.df_ids = self.df_ids.iloc[:1]
        self.version = version

    def add_hotel(self):
        # On crée un layout horizontal pour chaque ligne "hotel + date debut + date fin" créée
        hlayout = QHBoxLayout()

        # Création d'une liste déroulante de usernames et d'une autre liste déroulante composée des hôtels associés à chaque username, s'il y a lieu
        username_combobox, hotel_name_combobox = QComboBox(), QComboBox()

        # Récupération du username et de l'hôtel les plus longs pour fixer la largeur des comboboxes
        longest_username = max(self.username_list, key=len, default="")
        cw.setWidthFromString(username_combobox, longest_username)
        longest_hotel_name = max(self.hotel_name_list, key=len, default="")
        cw.setWidthFromString(hotel_name_combobox, longest_hotel_name)

        # Ajout aux comboboxes des usernames et de leur(s) hôtel(s) associé(s)
        for username in self.username_list:
            related_hotels = self.df_ids.loc[self.df_ids["username"] == username, "hotel_name"].to_list()
            username_combobox.addItem(username, related_hotels)
        username_combobox.currentIndexChanged.connect(
            lambda *args: self.update_hotel_name_combobox(username_combobox, hotel_name_combobox)
        )

        ##Initilisation des listes déroulantes
        self.update_hotel_name_combobox(username_combobox, hotel_name_combobox)

        # Création de 2 DateEdit personnalisés (voir classe cw.CustomDateEdit pour plus d'infos) pour sélectionner la période sur laquelle on souhaite modifier les prix
        date_edit_beg = cw.CustomDateEdit(date_min=self.today)
        date_edit_end = cw.CustomDateEdit()
        date_edit_beg.dateChanged.connect(lambda *args: self.update_date_edit_end(date_edit_beg, date_edit_end))
        self.update_date_edit_end(date_edit_beg, date_edit_end)

        # Button for deleting the line
        remove_button = cw.CustomToolButton(
            "", lambda *args: self.delete_line(hlayout), "Supprimer la ligne", self.remove_icon_path
        )

        # On insère le hlayout à l'avant dernière ligne du self.param_widget_vlayout (la dernière ligne contient toujours les boutons 'Ajouter' et 'Effacer tout'), puis on ajoute au hlayout les widgets créés
        self.param_widget_vlayout.insertLayout(self.param_widget_vlayout.count() - 1, hlayout)
        for widget in [username_combobox, hotel_name_combobox, date_edit_beg, date_edit_end, remove_button]:
            hlayout.addWidget(widget)

    def run_pricing(self):
        self.thread = QThread()
        self.worker = worker.Worker(self)
        self.worker.moveToThread(self.thread)

        # If widgets already exist, remove them and recreate them for a cleaner code
        # + allows for avoiding bugs if progressbar has been updated due to an error -> update via 'setStyleSheet' deletes all its parameters, so it no longer looks the same
        if self.pricing_hlayout.count() > 3:
            for i in [5, 4, 3]:
                cw.remove_widget_cleanly_at(i, self.pricing_hlayout)

        cancel_pricing_button = cw.CustomPushButton("Annuler", self.thread.requestInterruption, "Annuler le pricing")
        pricing_progressbar = cw.CustomProgressBar(range_=(0, 100), alignment=Qt.AlignCenter)
        pricing_label = cw.CustomLabel(fixed_width=200, word_wrap=True)  # For real time status
        for widget in [cancel_pricing_button, pricing_progressbar, pricing_label]:
            self.pricing_hlayout.addWidget(widget)

        # Handle events
        self.thread.started.connect(self.worker.run_pricing)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.set_ui_enabled)
        self.thread.finished.connect(lambda *args: cancel_pricing_button.setEnabled(False))
        self.thread.finished.connect(self.add_list_widget_separator)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.update_progressbar.connect(lambda value: self.update_progressbar(pricing_progressbar, value))
        self.worker.update_label.connect(lambda message, style_dict: self.update_label(pricing_label, message, **style_dict))
        self.worker.update_log_list_widget.connect(
            lambda message, style_dict: self.update_log_list_widget(message, **style_dict)
        )

        # Start thread
        self.set_ui_enabled(pricing_enabled=False)
        self.thread.start()

    def update_lists(self):
        """
        Update username and hotel lists
        """
        self.username_list = sorted(set(self.df_ids["username"]), key=str.lower)
        self.hotel_name_list = self.df_ids["hotel_name"].to_list()

    def update_progressbar(self, progressbar, value):
        if value >= 0:
            progressbar.setValue(value)
        else:
            progressbar.setStyleSheet("QProgressBar::chunk {background-color: red;}")

    def update_log_list_widget(self, message, **kwargs):
        """
        Update log list widget by inserting a new item and handling color
        """
        now = dt.datetime.now()
        self.log_list_widget.addItem("[{}]   {}".format(now.strftime("%H:%M"), message))

        for key, value in kwargs.items():
            if key == "color":
                self.log_list_widget.item(self.log_list_widget.count() - 1).setForeground(QColor(value))
            else:
                raise KeyError("Le mot clé '{}' choisi pour le style du dernier item du registre est invalide".format(key))

    def update_label(self, label: QLabel, message: str, **kwargs):
        """
        Same principle than update_log_list_widget, but for the label
        """
        label.setText(message)
        label.setStyleSheet("QLabel { color : black; }")
        for key, value in kwargs.items():
            if key == "color":
                label.setStyleSheet("QLabel { color : %s; }" % value)
            else:
                raise KeyError("Le mot clé '{}' choisi pour le style du label est invalide".format(key))

    def set_ui_enabled(self, pricing_enabled=True):
        """
        Enable or disable widgets to prevent bugs when the tools runs an action
        """
        widgets = [
            self.param_groupbox,
            self.no_edit_option,
            self.edit_option,
            self.run_pricing_button,
            self.restore_table_ids_button,
            self.save_table_ids_button,
        ]
        if pricing_enabled:
            self.param_groupbox.setStyleSheet("QGroupBox::title{ color: black; }")
            for widget in widgets:
                widget.setEnabled(True)
        else:
            self.param_groupbox.setStyleSheet("QGroupBox::title{ color: gray; }")
            for widget in widgets:
                widget.setEnabled(False)

    def add_list_widget_separator(self):
        item = QListWidgetItem()
        item.setFlags(Qt.NoItemFlags)
        self.log_list_widget.addItem(item)
        frame = QFrame()
        frame.setFrameShape(QFrame.HLine)
        self.log_list_widget.setItemWidget(item, frame)

        # On sélectionne le dernier message affiché dans la log_list_widget
        # self.log_list_widget.setCurrentRow(self.log_list_widget.count()-2)

    def update_date_edit_end(self, date_edit_beg, date_edit_end):
        date_value = date_edit_beg.date()
        date_edit_end.setMinimumDate(date_value)
        if date_value > date_edit_end.date():
            date_edit_end.setDate(date_value)

    def update_hotel_name_combobox(self, username_combobox, hotel_name_combobox):
        hotel_name_combobox.clear()
        related_hotels = username_combobox.currentData()
        if related_hotels:
            hotel_name_combobox.addItems(related_hotels)

    def delete_line(self, hlayout: QHBoxLayout):
        for i in reversed(range(hlayout.count())):
            cw.remove_widget_cleanly_at(i, hlayout)
        self.param_widget_vlayout.removeItem(hlayout)  # Remove hlayout

    def clear(self):
        # -1 because the last layout must not be deleted (it contains add_hotel_button and clear_button)
        for i in reversed(range(self.param_widget_vlayout.count() - 1)):
            item = self.param_widget_vlayout.itemAt(i)
            if item.layout() is not None:
                self.delete_line(item)
            # elif item.spacerItem():
            # 	self.param_widget_vlayout.removeItem(item)
            # elif item.widget() is not None:
            # 	self.param_widget_vlayout.removeWidget(item)
            # 	widget.setParent(None)

    # SETTINGS TAB
    def save_table_ids(self):
        df_from_table_ids = self.table_ids.to_df()

        # Delete empty rows
        new_df_ids = df_from_table_ids.loc[df_from_table_ids.astype(bool).any(axis=1)]

        if self.version == Version.FREE:
            new_df_ids = new_df_ids.iloc[:1]

        # If the content of the created df is not identical to self.df_ids, update self.df_ids and save it
        if not new_df_ids.equals(self.df_ids):
            self.df_ids = new_df_ids
            self.update_lists()
            new_df_ids.to_excel(self.ids_path, index=False)

        # Refill the table to delete empty rows
        if not new_df_ids.equals(df_from_table_ids):
            self.table_ids.fill(new_df_ids)
