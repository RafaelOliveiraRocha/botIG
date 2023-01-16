from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from time import sleep
import random
from selenium.webdriver.chrome.service import Service
from selenium import webdriver

# Seleciona o Chrome como navegador
service = Service(executable_path="/path/to/chromedriver")
driver = webdriver.Chrome(service=service)

# define o login com a conta e senha passadas


class instagramBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = webdriver.Chrome(service=service,
                                       executable_path="/home/rocha/Área de Trabalho/geckodriver-v0.32.0-linux64.tar.gz\geckodriver.exe")

    def login(self):
        driver = self.driver
        driver.get("https://www.instagram.com/")  # Navega para o site
        sleep(8)

        # buttonLogin = driver.find_element_by_xpath("//a[@href='/accounts/login/?source=auth_switcher']")
        # buttonLogin.click() #--> Caso a tela inicial do site peça pra clicar em login. Atualmente, pelo o que eu vi, a tela inicial já é a de login.
        # inputUser = driver.find_element_by_xpath("//input[@name='username']") **********************

        # Fazer login
        inputUser = driver.find_element("xpath", "//input[@name='username']")
        inputUser.click()
        inputUser.clear()
        inputUser.send_keys(self.username)
        inputPassword = driver.find_element(
            "xpath", "//input[@name='password']")
        inputPassword.click()
        inputPassword.clear()
        inputPassword.send_keys(self.password)
        inputPassword.send_keys(Keys.ENTER)
        sleep(15)
        self.commentHashtag('nfl')
        sleep(15)

    @staticmethod  # Digitar como humano.
    def typeHuman(frase, ondeDigitar):
        for letra in frase:
            ondeDigitar.send_keys(letra)
            sleep(random.randint(1, 5) / 30)

    # Seleciona a hash para pesquisar no IG
    def commentHashtag(self, hashtag):
        driver = self.driver
        driver.get("https://www.instagram.com/explore/tags/" + hashtag + "/")
        sleep(15)

        # Scroll na tela para carregar mais fotos
        for c in range(1, 2):
            driver.execute_script(
                'window.scrollTo(0, document.body.scrollHeight);')
            sleep(15)

        # Seleciona todos os hrefs da página visível e os guarda na lista
        hrefs = driver.find_elements(By.TAG_NAME, "a")
        picHrefs = [item.get_attribute('href') for item in hrefs]
        [href for href in picHrefs if '/p/' in href]
        print(hashtag + ' fotos ' + str(len(picHrefs)))

        # Faz um laço pela lista clicando e abrindo as fotos
        for i in picHrefs:
            driver.get(i)  # Clica na foto
            driver.execute_script(
                'window.scrollTo(0, document.body.scrollHeight);')  # Scroll após clicar para o input de comentário ficar visível e interativo
            sleep(7)
            try:
                # lista de comentários
                comments = ['Show!', 'Maneiro', 'Parabéns!',
                            'Legal', 'Supimpa', 'Uuuouu', 'Show de bola']

                # Clicar no input de comentário para digitar
                driver.find_element(
                    "xpath", "//textarea[@placeholder='Adicione um comentário...']").click()
                # guarda a referência do input para dizer depois para a função typeHuman onde digitar
                inputComment = driver.find_element(
                    "xpath", "//textarea[@placeholder='Adicione um comentário...']")
                sleep(random.randint(2, 5))
                # Chamada a função para digitar o comentário
                self.typeHuman(random.choice(comments), inputComment)
                sleep(random.randint(10, 20))
                # clicar no botão postar
                driver.find_element("xpath", "//div[@class='x1i10hfl x1qjc9v5 xdl72j9 x2lah0s xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r x2lwn1j xeuugli x1hl2dhg xggy1nq x1ja2u2z x1t137rt x1q0g3np x1lku1pv x1a2a7pz xjyslct x9f619 x1ypdohk x1i0vuye xwhw2v2 x17ydfre xl56j7k x1f6kntn x2b8uid xlyipyv x87ps6o x14atkfc x1lcm9me x1yr5g0i xrt01vj x10y3i5r x1d5wrs8 x1v8p93f xogb00i x16stqrj x1ftr3km x13fuv20 xu3j5b3 x1q0q8m5 x26u7qi x972fbf xcfux6l x1qhh985 xm0m39n xt0psk2 xexx8yu x4uap5 x18d9i69 xkhd6sd x1n2onr6 xjbqb8w xt7dq6l x173jzuc']").click()
                sleep(10)
                # driver.find_element(By.CLASS_NAME, "_ab6-").click()
                # sleep(10)

            except Exception as e:
                print(e)
                sleep(5)


rochaBot = instagramBot('user_name', 'password')
rochaBot.login()
