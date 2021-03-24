"""Since target server yet daoesn't have API support, this pipeline implements basic fuctionality to fill it with
items """

import requests
import re
import json
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import selenium.common.exceptions as se
from marketplace.credentials import Marketplace
from scrapy.exceptions import DropItem, CloseSpider


class MarketplacePipeline:
    logger = logging.getLogger('MarketplacePipeLogger')
    logger.setLevel(logging.DEBUG)

    options = Options()
    options.add_argument('--headless')

    token = ''
    headers = {'Accept': '*/*',
               'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/89.0.4389.82 Safari/537.36",
               }

    def get_token(self, url, spider):
        init_response = requests.get(url=url, headers=self.headers)
        token = re.search(r'csrf-token" content="(.+)\b', init_response.text)
        try:
            token = token.group(1)
            self.logger.info('Token received')
            return token, init_response.headers
        except AttributeError:
            self.logger.error('Unable to receive token')
            raise CloseSpider('token not received')

    def create_product(self, item, domain):

        p_type = 'simple'
        attribute_family_id = 2
        data = {
            '_token': self.token,
            'type': p_type,
            'attribute_family_id': attribute_family_id,
            'sku': item['sku']
        }
        return requests.post(url=domain + '/catalog/products/create/', data=data, headers=self.headers)

    def edit_product(self, pid, item, domain):
        data = {
            '_token': self.token,
            '_method': 'PUT',
            'channel': 'default',
            'sku': item['sku'],
            'locale': 'en',
            'product_number': item['product_number'],
            'name': item['name'],
            'url_key': item['url_key']+'aaaaa',
            'brand': 11,
            'short_description': '<p>' + item['short_description'] + '</p>',
            'description': '<p>' + item['description'] + '</p>',
            'price': item['price'],
            'weight': item['weight'],
            'new': 1,
            'visible_individually': 1,
            'status': 1,
            'inventories[1]': item['quantity'],
            'categories[]': 7,
            'meta_title': item['meta_title'],
            'meta_description': item['meta_description'],
            'braclet_material': item.get('braclet_material'),
            'case_material': item.get('case_material'),
            'water_resistance': item.get('waterresistance'),
            'color_of_the_dial': item.get('Colorofthedial'),
            'body_diameter': item.get('bodydiameter'),
            'model': item.get('model'),
            'series': item.get('series')
        }

        url = domain + '/catalog/products/edit/' + pid
        return requests.post(url=url, data=data, headers=self.headers)

    def open_spider(self, spider):
        self.logger.info('STARTING MY AWESOME SPIDER')
        self.token, init_headers = self.get_token(Marketplace.domain + '/login', spider)
        self.headers['Cookie'] = re.search(r'crypto_exchange.+', init_headers['Set-Cookie']).group()
        payload = {
            'email': Marketplace.email,
            'password': Marketplace.password,
            '_token': self.token
        }

        login_response = requests.post(url=Marketplace.domain + '/login', headers=self.headers, data=payload)
        if login_response.status_code == 200 and re.search(r'<title>\s+Dashboard', login_response.text):
            self.headers['Cookie'] = re.search(r'crypto.+', login_response.headers['Set-Cookie']).group()
            self.logger.info('Marketplace login successfully')
        else:
            self.logger.error('Login failed, login request status is {}'.format(login_response.status_code))
            raise CloseSpider('loginfailed')

    def process_item(self, item, spider):

        product = self.create_product(item=item, domain=Marketplace.domain)
        pid = re.search(r'productId:\s+(\d+)', product.text)
        if not pid:
            self.logger.warning('Product not added {}'.format(json.dumps(item)))
            raise DropItem('item not added')
        pid = pid.group(1)
        finish_product = self.edit_product(pid, item, Marketplace.domain)
        if finish_product.status_code == 200:
            self.logger.info('product added')
        else:
            self.logger.error('editing failed')
            raise DropItem('item not added')
        self.insert_image(pid, item, Marketplace)
        return item

    def insert_image(self, pid, item, user):
        try:
            driver = webdriver.Chrome(options=self.options, executable_path='./chromedriver')
        except se.WebDriverException:
            self.logger.exception('Browser startup failed')
        else:
            try:
                driver.get(url=user.domain + 'catalog/products/edit/' + pid)
                username_form = driver.find_element_by_id('email')
                password_form = driver.find_element_by_id('password')
                username_form.send_keys(user.email)
                password_form.send_keys(user.password)
                driver.implicitly_wait(5)
                login_button = driver.find_element_by_class_name('btn.btn-xl.btn-primary').click()
                driver.implicitly_wait(5)
                add_image_btn = driver.find_element_by_xpath("//label[contains(text(), 'Add Image')]")
                driver.execute_script('javascript:arguments[0].click()', add_image_btn)
                hidden_input = driver.find_element_by_name('images[]')
                currentpath = os.getcwd()
                img_path = os.path.join(currentpath, 'src', item['images'][0]['path'])
                hidden_input.send_keys(img_path)
                driver.implicitly_wait(5)
                driver.find_element_by_xpath('//div[@class="page-action"]/button').click()
                driver.implicitly_wait(5)
                driver.close()
            except Exception as BrowserException:
                self.logger.error('{}, args - {}'.format(BrowserException.message, BrowserException.args))
                self.logger.error('image based content not found {}'.format(json.dumps(item)))
