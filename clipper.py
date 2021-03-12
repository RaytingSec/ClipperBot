import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class ClipperBot(object):
	username = ''
	password = ''
	payment_method = ''
	card_cvv = ''

	endpoints = {
		"login": "https://www.clippercard.com/ClipperCard/loginFrame.jsf",
		"dashboard": "https://www.clippercard.com/ClipperCard/dashboard.jsf",
		"addvalue": "https://www.clippercard.com/ClipperCard/manage.jsf"
	}

	def __init__(self, driver=None):
		super(ClipperBot, self).__init__()
		self.driver = driver
		self.cards = []

	def load_config(self):
		with open('config.json') as f:
			config = json.load(f)

		self.username = config['username']
		self.password = config['password']
		self.payment_method = config['payment_method']
		self.card_cvv = config['card_cvv']

	def login(self):
		print("Loading webdriver")
		self.driver = driver = webdriver.Firefox()
		print("Webdriver loaded")

		driver.get(self.endpoints['login'])
		try:
			loginfound = EC.visibility_of_element_located((By.CSS_SELECTOR, "form#j_idt13"))
			WebDriverWait(driver, 10).until(loginfound)
		except TimeoutException as e:
			print("Timout on login form")
			raise e
		else:
			print("Loaded login page")

		login_form = driver.find_element_by_css_selector("form#j_idt13")

		user_input = login_form.find_element_by_css_selector("input#j_idt13\:username")
		user_input.clear()
		user_input.send_keys(self.username)
		pass_input = login_form.find_element_by_css_selector("input#j_idt13\:password")
		pass_input.clear()
		pass_input.send_keys(self.password)

		login_form.find_element_by_css_selector("input#j_idt13\:submitLogin").click()
		# driver.implicitly_wait(10)  # Ensure page loaded before proceding
		try:
			WebDriverWait(driver, 10).until(EC.url_matches(self.endpoints['dashboard']))
		except TimeoutException as e:
			print("Timout on loading dashboard")
			raise e
		else:
			print("Logged in, dashboard loaded")

	def get_cards(self):
		driver = self.driver

		if driver.current_url != self.endpoints['dashboard']:
			print("Navigating to dashboard")
			driver.get(self.endpoints['dashboard'])
		else:
			print("Already on dashboard")

		try:
			cardsfound = EC.visibility_of_element_located((By.CSS_SELECTOR, "div.greyBox2"))
			WebDriverWait(driver, 10).until(cardsfound)
		except TimeoutException as e:
			print("Timout on loading dashboard")
			raise e
		else:
			print("Loaded dashboard")

		cards_element = driver.find_element_by_css_selector("div.greyBox2")
		cardinfo_elements = cards_element.find_elements_by_css_selector("div.cardInfo")
		cards = list(zip(*(iter(cardinfo_elements),) * 2))
		print("Found {} cards".format(len(cards)))
		self.cards = [self.buildcard(card) for card in cards]

	def buildcard(self, card:list) -> dict:
		name = card[0].find_element_by_css_selector("span.displayName").text
		number = card[0].find_elements_by_css_selector("div.fieldData")[2].text
		value = "$0.0"
		# try:
		# 	value = card[1].find_elements_by_css_selector("div.infoDiv")[3].find_element_by_css_selector("div.fieldData").text  # possibly prone to breaking
		# except Exception as e:
		# 	print("No value found for " + name, e)
		# addvalue_button = card[1].find_element_by_xpath("//input[@value='Add Value']")

		card = dict(
			name=name,
			number=number,
			value=value
			# addvalue_button=addvalue_button
		)
		print("Built card {}".format(name))
		return card

	def add_value(self, cardname, cashvalue=1.25, demo=False):
		assert cashvalue >= 1.25  # Need  to load at least 1.25
		if demo:
			print("DRY RUN")

		driver = self.driver

		driver.get(self.endpoints["addvalue"])
		# WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//input[@value='Checkout']")))
		cardoptions = driver.find_element_by_css_selector("table#mainForm\:selectCard")
		for row in cardoptions.find_elements_by_css_selector("tr"):
			if cardname in row.text:
				print("Select Clipper card: {}".format(row.text))
				row.find_element_by_css_selector("input").click()
				break
		driver.find_element_by_css_selector("input#mainForm\:modifyCardThreeBtn").click()

		# skip dialog
		if driver.find_element_by_css_selector("div.ui-dialog.ui-widget.ui-widget-content.ui-corner-all.ui-front.ui-draggable.ui-resizable").is_displayed():
			driver.find_element_by_css_selector("div#contAddValue").click()

		WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//input[@value='Checkout']")))
		# add cash
		driver.find_element_by_css_selector("a#cash").click()
		# enter value
		driver.find_element_by_css_selector("input#mainForm\:addCashInput").send_keys(str(cashvalue))
		# ensure autoload disabled
		driver.find_element_by_css_selector("input#mainForm\:autoloadCash\:1").click()
		# add to cart
		driver.find_element_by_css_selector("div#addCashBTN.productAdd").click()
		# Checkout
		driver.find_element_by_xpath("//input[@value='Checkout']").click()

		WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//input[@value='Next']")))
		# Choose card
		paymentmethods = driver.find_element_by_css_selector("table#mainForm\:payMethod")
		for row in paymentmethods.find_elements_by_css_selector("tr"):
			if self.payment_method in row.text:
				print("Selected payment card: {}".format(row.text))
				row.find_element_by_css_selector("input").click()
				break
		# Enter CVV
		driver.find_element_by_css_selector("div#existingCard div.textAnswer input.securityCode").send_keys(self.card_cvv)
		# Checkout
		driver.find_element_by_xpath("//input[@value='Next']").click()

		WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//input[@value='Place Order']")))
		# Accept terms and conditions
		driver.find_element_by_css_selector("input#acceptTaC").click()
		# Order
		if not demo:
			driver.find_element_by_xpath("//input[@value='Place Order']").click()
		print("Submitted order")

	def exit(self):
		print("Closing webdriver")
		self.driver.close()


if __name__ == '__main__':
	clipper = ClipperBot()
	clipper.load_config()
	clipper.login()
	clipper.get_cards()
	print(clipper.cards)
	clipper.add_value("Primary Transit Card", 50.0, demo=False)
	clipper.exit()
