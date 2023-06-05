from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver import Edge
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from subprocess import CREATE_NO_WINDOW
from selenium.webdriver.common.keys import Keys
import datetime as dt
import sys
import time
import pickle
import os
from constants import ROOT_PATH, SETTINGS_DICT, EDGE_VERSION

# Idée : au lieu de créer plusieurs "if worker is not None", on peut en mettre un seul au début pour créer un alias (appelé display par ex) des fonctions print ou emit selon le cas
# -> une unique fonction pour les 2 cas
# Essayer d'avoir un seul tronc commun avec des if dans la méthode check_prices


class DedgeBot:
    def __init__(self, desktop_size=None):
        # Settings
        self.cookies_path = os.path.join(ROOT_PATH, SETTINGS_DICT["cookies_path"])
        self.desktop_size = desktop_size
        self.months_dict = {
            "janv.": 1,
            "févr.": 2,
            "mars": 3,
            "avr.": 4,
            "mai": 5,
            "juin": 6,
            "juil.": 7,
            "août": 8,
            "sept.": 9,
            "oct.": 10,
            "nov.": 11,
            "déc.": 12,
        }
        self.reverse_months_dict = {value: key for key, value in self.months_dict.items()}

        # Driver states
        self.driver_has_been_prepared = False
        self.driver_has_already_been_created = False

    def prepare_driver(self):
        # Il faut compter une erreur d'environ 6px sur la largeur de l'écran pour obtenir la bonne position (garder cette variable dans le programme tant que ce pb n'est pas réglé)
        # Il semble aussi que la taille de la fenêtre du browser obtenue ne corresponde pas exactement non plus à celle souhaitée (à approfondir).
        # Il y a notamment une différence de taille avec celle de l'ui, alors que cette dernière a reçu la même taille en argument
        width_error = 6
        options = Options()
        if self.desktop_size is not None:
            options.add_argument("force-device-scale-factor=1")  # Forcer le facteur de mise à l'échelle (ici 100%)
            # options.add_argument('high-dpi-support=1')  # Pas utile a priori
            options.add_argument(
                "--window-size={},{}".format(self.desktop_size.width() // 2 + 13, self.desktop_size.height() + 7)
            )  # 13 et 7 sortent de nulle part, c'est juste pour bien coller à mon écran
            options.add_argument("--window-position={},0".format(self.desktop_size.width() // 2 - width_error))
            # Alternative : self.driver.set_window_size(width, height) et self.driver.set_window_position(x, y) à la suite de Edge(),
            # mais les changements se font après la création de la fenêtre, donc on voit le mouvement de position (moche)
        else:
            options.add_argument("--start-maximized")

        # Installation automatique du driver
        if EDGE_VERSION is not None:
            service = Service(EdgeChromiumDriverManager(version=EDGE_VERSION).install())
        else:
            service = Service(EdgeChromiumDriverManager().install())

        service.creationflags = CREATE_NO_WINDOW  # Empêche selenium d'ouvrir un terminal grâce à 'CREATE_NO_WINDOW'

        self.options = options
        self.service = service

        # Maj de l'état du driver
        self.driver_has_been_prepared = True

    def create_driver(self):
        # Instanciation du driver (et ouverture du navigateur Microsoft Edge)
        self.driver = Edge(service=self.service, options=self.options)

        # Durée d'attente implicite pour que les éléments de pages soient trouvés
        self.driver.implicitly_wait(60)

        # Ouverture d'une page D-Edge
        self.go_to_home_page()

        # Ajout des cookies déjà créés auparavant (de telle sorte qu'on n'aura plus à s'en occuper pour le reste de la session)
        if self.cookies_path is not None:
            self.add_cookies()

        # Maj de l'état du driver
        self.driver_has_already_been_created = True

    # Accès à la page d'accueil du site D-Edge
    def go_to_home_page(self):
        self.driver.get("https://login.availpro.com/")

    # Connexion au compte D-Edge de l'hôtel avec création du cookie en option
    def login(self, username, password, create_cookie=False, worker=None):
        if worker is not None:
            current_url = self.driver.current_url

            # Connexion
            message = f"{username} : Connexion au compte D-Edge"
            worker.emit_signals(message, message)
            self.driver.find_element_by_xpath('//*[@id="text-id-login"]').send_keys(
                username
            )  # Entrer l'identifiant de l'hôtel
            self.driver.find_element_by_xpath('//*[@id="input-password"]').send_keys(password)  # Entrer le mot de passe
            self.driver.find_element_by_xpath('//input[@value="Login"]').click()  # Cliquer sur le bouton connecter

            # [Explicit wait]
            while current_url == self.driver.current_url:
                worker.exit_if_interruption_requested()

            # Check si le cookie a déjà été créé
            if "https://extranet.availpro.com/Device" not in self.driver.current_url:
                return

            # Attendre à l'infini tant que le code n'a pas été entré (permet de mettre un implicit wait plus petit car ce dernier n'est pas utilisé pour cette tâche) [Explicit wait]
            worker.emit_signals("{} : Veuillez entrer le mot de passe reçu par email".format(username))
            while "https://extranet.availpro.com/Device" in self.driver.current_url:
                time.sleep(1)
                worker.exit_if_interruption_requested()
                ###
                ### Entrer manuellement le code reçu par email###
                ###

            # Check si besoin de créer le cookie
            if create_cookie:
                # On s'assure d'être dans la page principale en exécutant une requête inutile après la connexion pour garantir la récupération du cookie
                # -> sanity check personnel (pas nécessaire normalement)
                self.driver.find_element_by_xpath('//a[@data-name="PriceAndPlanningSection"]')

                # Retour à la page d'accueil pour pouvoir créer le cookie
                self.go_to_home_page()

                # Création du cookie
                message = "{} : Création du cookie".format(username)
                worker.emit_signals(message, message)
                with open(self.cookies_path, "wb") as cookies_file:
                    pickle.dump(self.driver.get_cookies(), cookies_file)
                message = "{} : Cookie créé".format(username)
                worker.emit_signals(message, message)

                # Reconnexion
                self.login(
                    username, password, create_cookie=True, worker=worker
                )  # create_cookie=True non nécessaire normalement

        else:
            current_url = self.driver.current_url

            print("{} : Connexion au compte D-Edge".format(username))
            self.driver.find_element_by_xpath('//*[@id="text-id-login"]').send_keys(
                username
            )  # Entrer l'identifiant de l'hôtel
            self.driver.find_element_by_xpath('//*[@id="input-password"]').send_keys(password)  # Entrer le mot de passe
            self.driver.find_element_by_xpath('//input[@value="Login"]').click()  # Cliquer sur le bouton connecter

            # [Explicit wait]
            while current_url == self.driver.current_url:
                pass

            if "https://extranet.availpro.com/Device" not in self.driver.current_url:
                return

            # [Explicit wait]
            print("{} : Veuillez entrer le mot de passe reçu par email".format(username))
            while "https://extranet.availpro.com/Device" in self.driver.current_url:
                time.sleep(1)

            if create_cookie:
                self.driver.find_element_by_xpath('//a[@data-name="PriceAndPlanningSection"]')
                self.go_to_home_page()
                print("{} : Création du cookie".format(username))
                with open(self.cookies_path, "wb") as cookies_file:
                    pickle.dump(self.driver.get_cookies(), cookies_file)
                print("{} : Cookie créé".format(username))
                self.login(username, password, create_cookie=True)

    def add_cookies(self):
        # Ouverture du fichier de cookies s'il n'est pas vide
        if os.path.getsize(self.cookies_path) > 0:
            with open(self.cookies_path, "rb") as cookies_file:
                cookies = pickle.load(cookies_file)
                for cookie in cookies:
                    ###Bout de code à ajouter sous selenium 4 pour ne pas avoir d'erreur (vérifier au fur et à mesure du temps si c'est juste une erreur temporaire)
                    if "sameSite" in cookie:
                        if cookie["sameSite"] == "None":
                            cookie["sameSite"] = "Strict"
                    ###
                    self.driver.add_cookie(cookie)

    @staticmethod
    def format_price(raw_price, temp_date):
        if isinstance(raw_price, int):
            good_price = str(raw_price)
        elif isinstance(raw_price, float):
            # Si le nombre décimal est en fait un entier qui a été converti en float TERMINANT PAR .0 par le fichier excel ou par pandas, on le reconvertit en entier sans renvoyer d'erreur
            if raw_price.is_integer():
                good_price = str(int(raw_price))
            # Si le nombre décimal est en fait un entier qui a été converti en float TERMINANT PAR .99... par le fichier excel ou par pandas, on le reconvertit en entier sans renvoyer d'erreur
            elif abs(round(raw_price) - raw_price) < 0.00001:
                good_price = str(round(raw_price))
            else:
                raise TypeError(
                    "Le prix {} à la date {} est un nombre décimal. Veuillez entrer un nombre entier".format(
                        raw_price, temp_date.strftime("%d/%m/%Y")
                    )
                )
        elif isinstance(raw_price, str):
            # On remplace les virgules par des points, s'il y a lieu, pour faciliter une éventuelle conversion en nombre entier
            raw_price = raw_price.replace(",", ".")
            try:
                floated_price = float(raw_price)
                if floated_price.is_integer():
                    good_price = str(int(floated_price))
                else:
                    raise TypeError(
                        "Le prix {} à la date {} est un nombre décimal. Veuillez entrer un nombre entier".format(
                            raw_price, temp_date.strftime("%d/%m/%Y")
                        )
                    )
            except:
                raise TypeError(
                    "Le prix {} à la date {} est de type {}. Veuillez entrer un nombre entier".format(
                        raw_price, temp_date.strftime("%d/%m/%Y"), type(raw_price)
                    )
                )
        else:
            raise TypeError(
                "Le prix {} à la date {} est de type {}. Veuillez entrer un nombre entier".format(
                    raw_price, temp_date.strftime("%d/%m/%Y"), type(raw_price)
                )
            )

        return good_price

    def check_prices(
        self,
        hotel_is_alone,
        room_type,
        price_type,
        beg_date,
        end_date,
        df_prices,
        method="no-edit",
        hotel_name=None,
        worker=None,
    ):
        hotel_name = hotel_name if hotel_name else "NO-HOTEL-NAME"

        # Cas anormal où la date de début est supérieure à la date de fin
        if beg_date > end_date:
            raise Exception(
                "La date de début ({}) est supérieure à la date de fin ({})".format(
                    beg_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y")
                )
            )

        message = f"{hotel_name} : Accès à l'interface de prix"
        if worker is not None:
            worker.emit_signals(message, message)
        else:
            print(message)

        if not hotel_is_alone:
            if hotel_name != "NO-HOTEL-NAME":
                self.driver.find_element_by_xpath('//a[@class="header-hotel-selector__value"]').click()
                self.driver.find_element_by_xpath(
                    '//a[@class="header-hotel-selector__result__item" and text()[contains(., "{}")]]'.format(hotel_name)
                ).click()
            else:
                raise Exception("Veuillez renseigner le nom de l'hôtel pour assurer le bon fonctionnement du pricing")

        if worker is not None:
            worker.exit_if_interruption_requested()

        # Aller à la section Prix et Planning
        self.driver.find_element_by_xpath('//a[@data-name="PriceAndPlanningSection"]').click()

        if worker is not None:
            worker.exit_if_interruption_requested()

        # Cliquer sur un prix pour accéder à l'interface de prix
        self.driver.find_element_by_xpath('//table[@class="room"]//tr[@class="price"]/td[3]').click()

        if worker is not None:
            worker.exit_if_interruption_requested()

        # Sélectionner la grille de référence
        ##Sélectionner le type de chambre
        self.driver.find_element_by_xpath('//*[@id="roomSelector"]/option[text()="{}"]'.format(room_type)).click()
        ##Sélectionner le type de prix
        self.driver.find_element_by_xpath('//*[@id="rateSelector"]/option[text()="{}"]'.format(price_type)).click()

        if worker is not None:
            worker.exit_if_interruption_requested()

        # Récupérer la date en cours
        current_date = self.driver.find_element_by_class_name("dateLabel").text
        day, month, year = current_date.split()
        current_date = dt.date(int(year), self.months_dict[month], int(day))

        # Atteindre la page où se situe la beg_date
        while not (0 <= (beg_date - current_date).days < 14):
            if worker is not None:
                worker.exit_if_interruption_requested()

            current_url = self.driver.current_url

            if beg_date.year < current_date.year:
                self.driver.find_elements_by_xpath('//div[@class="months"]/a')[0].click()
            elif beg_date.year > current_date.year:
                self.driver.find_elements_by_xpath('//div[@class="months"]/a')[-1].click()
            elif beg_date.month - current_date.month < -5:
                self.driver.find_elements_by_xpath('//div[@class="months"]/a')[0].click()
            elif beg_date.month - current_date.month > 6:
                self.driver.find_elements_by_xpath('//div[@class="months"]/a')[-1].click()
            elif beg_date.month != current_date.month:
                beg_date_month_in_letters = self.reverse_months_dict[beg_date.month]
                self.driver.find_element_by_xpath(
                    '//div[@class="months"]/a[text()="{}"]'.format(beg_date_month_in_letters)
                ).click()
            elif beg_date < current_date:
                self.driver.find_element_by_xpath('//span[@class="prevnext"]/a[text()="14j. précédents"]').click()
            else:
                self.driver.find_element_by_xpath('//span[@class="prevnext"]/a[text()="14j. suivants"]').click()

            # Sanity check : on attend bien que la nouvelle page s'affiche (via vérification de l'URL) avant de récupérer la nouvelle date [Explicit wait]
            while current_url == self.driver.current_url:
                pass

            # Mise à jour de la date en cours
            current_date = self.driver.find_element_by_class_name("dateLabel").text
            day, month, year = current_date.split()
            current_date = dt.date(int(year), self.months_dict[month], int(day))

        # Message de début du pricing
        message = f"{hotel_name} : Début du pricing"
        if worker is not None:
            worker.emit_signals(message, message)
        else:
            print(message)

        date_idx = 0
        nb_days = (end_date - beg_date).days + 1

        # Insertion des prix Excel dans l'interface pour les dates comprises entre beg_date et end_date
        if method == "edit":
            any_modified_price = False
            temp_date = beg_date
            count = (temp_date - current_date).days
            while temp_date <= end_date:
                df_raw_price = df_prices.loc[df_prices["Date"] == temp_date, "Price"]
                if not df_raw_price.empty:
                    # Prix Excel
                    raw_price = df_raw_price.item()
                    good_price = self.format_price(raw_price, temp_date)

                    # Prix D-Edge
                    price_to_check = self.driver.find_element_by_xpath(
                        '//tr[@type="RatePrice"]/td[@day="{}"]//input[@id="Price"]'.format(count)
                    )
                    price_to_check_value = price_to_check.get_attribute("value")

                    # On clique sur le prix pour être bien sûr de faire apparaître le bouton d'enregistrement
                    price_to_check.click()

                    if good_price != price_to_check_value:
                        price_to_check.send_keys(Keys.CONTROL + "a")
                        price_to_check.send_keys(Keys.DELETE)
                        price_to_check.send_keys(good_price)

                        message = "{} : {} : Prix modifié : {} --> {}".format(
                            hotel_name, temp_date.strftime("%d/%m/%Y"), price_to_check_value, good_price
                        )
                        if worker is not None:
                            worker.emit_signals(log_list_widget_message=message)
                        else:
                            print(message)

                        if not any_modified_price:
                            any_modified_price = True
                            # Si on n'a modifié que le dernier prix de la quatorzaine de jours, on clique sur le premier prix (ou n'importe lequel autre que le dernier) pour faire apparaître le bouton d'enregistrement
                            if count == 13:
                                self.driver.find_element_by_xpath(
                                    '//tr[@type="RatePrice"]/td[@day="0"]//input[@id="Price"]'
                                ).click()
                else:
                    raise Exception(
                        "La date {} n'est pas dans le dataframe. Veuillez vérifier votre fichier Excel".format(
                            temp_date.strftime("%d/%m/%Y")
                        )
                    )

                date_idx += 1
                message = "{} : Pricing en cours ({}/{})".format(hotel_name, date_idx, nb_days)
                if worker is not None:
                    # Mise à jour de la barre de progression et du label
                    worker.date_idx += 1
                    pct = int(worker.date_idx / worker.total_nb_days * 100)
                    worker.emit_signals(message, progressbar_value=pct)

                    worker.exit_if_interruption_requested()
                else:
                    print(message)

                temp_date += dt.timedelta(days=1)
                count += 1
                if count == 14:
                    if any_modified_price:
                        # Enregistrement des modifications
                        self.driver.find_element_by_name("savePlanning").click()

                        # Réinitialisation du booléen indiquant si des prix ont été modifiés ou non sur la quatorzaine de jours
                        any_modified_price = False

                        # Gestion du moment précis auquel on doit cliquer sur le bouton '14j. suivants'
                        ##Juste après avoir modifié au moins un prix (puis avoir cliqué n'importe où), tous les éléments permettant de passer à une autre date sont désactivés (leur code html contient disabled="disabled") jusqu'à ce que les prix soient bien enregistrés
                        ##Ainsi, si l'on cherche un des ces éléments (ex: bouton '14j. suivants') durant ce processus et qu'on lance la méthode 'click', un comportement non souhaité se produit : selenium trouve l'élement et clique dessus (MAIS RIEN NE SE PASSE)
                        ##--> l'implicit wait ne peut donc pas correctement faire son travail, i.e. attendre que le bouton devienne clickable avant de clicker, car il est toujours clickable (tout comme du texte l'est)!
                        ##Toutes les solutions testées :
                        ## Ce qui fonctionne :						- Attendre que le message "Les modifications ont bien été enregistrées. " apparaisse : driver.find_element_by_xpath('//span[text()="Les modifications ont bien été enregistrées. "]')
                        ##											- Attendre que le bouton "Enregistré" apparaisse : code similaire à l'alternative précédente (pas testé mais doit fonctionner)
                        ##											- Attendre que le bouton '14j. suivants' soit "activé" (dès que le mot-clé "disabled" disparaît) :
                        ##					SOLUTION ACTUELLE -->		- driver.find_element_by_xpath('//span[@class="prevnext"]/a[text()="14j. suivants" and not(@disabled)]') (utilisation directe du xpath) (plus concis, plus propre, et certainement plus fiable)
                        ##												- while element.get_attribute('disabled') != None: pass
                        ##												- while driver.execute_script("return arguments[0].hasAttribute('disabled');", element): pass (en utilisant du code JS)(semble plus lent)(l'implicit wait peut faire son travail correctement)
                        ## Ce qui ne fonctionne pas : 				- driver.execute_script("arguments[0].click()", element)
                        ##											- ActionChains(driver).move_to_element(element).perform() puis element.click()
                        ##											- while not element.is_enabled(): pass (voir documentation pour l'explication)
                        ##											- idem pour element_to_be_clikable, active, ... car l'élément est bien clickable, c'est juste que rien ne se produit car il est disabled (grisé)
                        ### en remplaçant, dans les codes ci-dessus, element par --> driver.find_element_by_xpath('//span[@class="prevnext"]/a[text()="14j. suivants"]')

                    # Passage à la page suivante / Mise à jour de la date en cours : on clique sur le bouton suivant et on attend bien (via vérification de l'URL) que la nouvelle page s'affiche avant de récupérer la nouvelle date
                    current_url = self.driver.current_url
                    self.driver.find_element_by_xpath(
                        '//span[@class="prevnext"]/a[text()="14j. suivants" and not(@disabled)]'
                    ).click()
                    while current_url == self.driver.current_url:
                        pass

                    # Sanity check de la date [Explicit wait]
                    current_date_temp = self.driver.find_element_by_class_name("dateLabel").text
                    day, month, year = current_date_temp.split()
                    current_date_temp = dt.date(int(year), self.months_dict[month], int(day))
                    if current_date_temp != current_date + dt.timedelta(days=14):
                        raise Exception("Une erreur s'est produite durant le changement de date")

                    current_date = current_date_temp

                    # Réinitialisation du compteur
                    count = 0

            # On enregistre les modifications des dernières dates
            if any_modified_price:
                # On clique sur le dernier prix pour être sûr de faire apparaître le bouton d'enregistrement
                self.driver.find_element_by_xpath('//tr[@type="RatePrice"]/td[@day="13"]//input[@id="Price"]').click()
                self.driver.find_element_by_name("savePlanning").click()
                # Par précaution, on attend que l'enregistrement soit bien effectué avant d'aller à la page d'accueil dans le cas où il y a plusieurs hôtels à pricer
                self.driver.find_element_by_xpath('//span[text()="Les modifications ont bien été enregistrées. "]')

        # Vérification des prix dans l'interface par comparaison aux prix Excel pour les dates comprises entre beg_date et end_date
        elif method == "no-edit":
            temp_date = beg_date
            count = (temp_date - current_date).days
            while temp_date <= end_date:
                df_raw_price = df_prices.loc[df_prices["Date"] == temp_date, "Price"]
                if not df_raw_price.empty:
                    # Prix Excel
                    raw_price = df_raw_price.item()
                    good_price = self.format_price(raw_price, temp_date)

                    # Prix D-Edge
                    price_to_check = self.driver.find_element_by_xpath(
                        '//tr[@type="RatePrice"]/td[@day="{}"]//input[@id="Price"]'.format(count)
                    )
                    price_to_check_value = price_to_check.get_attribute("value")

                    if good_price != price_to_check_value:
                        message = "{} : {} : Prix D-Edge = {} != {} = Prix Excel".format(
                            hotel_name, temp_date.strftime("%d/%m/%Y"), price_to_check_value, good_price
                        )
                        if worker is not None:
                            worker.emit_signals(log_list_widget_message=message)
                        else:
                            print(message)
                else:
                    raise Exception(
                        "La date {} n'est pas dans le dataframe. Veuillez vérifier votre fichier Excel".format(
                            temp_date.strftime("%d/%m/%Y")
                        )
                    )

                date_idx += 1
                message = "{} : Pricing en cours ({}/{})".format(hotel_name, date_idx, nb_days)
                if worker is not None:
                    # Mise à jour de la barre de progression et du label
                    worker.date_idx += 1
                    pct = int(worker.date_idx / worker.total_nb_days * 100)
                    worker.emit_signals(message, progressbar_value=pct)

                    worker.exit_if_interruption_requested()
                else:
                    print(message)

                temp_date += dt.timedelta(days=1)
                count += 1
                if count == 14:
                    # Passage à la page suivante / Mise à jour de la date en cours : on clique sur le bouton suivant et on attend bien (via vérification de l'URL) que la nouvelle page s'affiche avant de récupérer la nouvelle date
                    current_url = self.driver.current_url
                    self.driver.find_element_by_xpath('//span[@class="prevnext"]/a[text()="14j. suivants"]').click()
                    while current_url == self.driver.current_url:
                        pass

                    # Sanity check de la date [Explicit wait]
                    current_date_temp = self.driver.find_element_by_class_name("dateLabel").text
                    day, month, year = current_date_temp.split()
                    current_date_temp = dt.date(int(year), self.months_dict[month], int(day))
                    if current_date_temp != current_date + dt.timedelta(days=14):
                        raise Exception("Une erreur s'est produite durant le changement de date")

                    current_date = current_date_temp

                    # Réinitialisation du compteur
                    count = 0

        # Message de fin du pricing
        message = f"{hotel_name} : Pricing terminé"
        if worker is not None:
            worker.emit_signals(message, message)
        else:
            print(message)

    # Delete the bot and return to the cmd
    def destroy(self):
        self.driver.quit()
        sys.exit(0)
