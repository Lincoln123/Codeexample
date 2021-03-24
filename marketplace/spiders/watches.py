"""This spider scrapes watch items from jacobs&co official website"""

import scrapy
from marketplace.items import WatchesItem
import re
from marketplace.watch_attributes import WatchAttributes


class WatchesSpider(scrapy.Spider):
    name = 'watches'
    allowed_domains = ['jacobandco.com']
    start_urls = [
        'https://jacobandco.com/timepiece-prices',
    ]

    def parse(self, response):
        """this method scrapes watch models from grid of the watches"""
        grid_links = response.xpath('//div[@class="products grid"]/a/@href').getall()
        prices = response.xpath(
            '//div[@class="products grid"]/a//span[@class="price-item"]/@data-start-price').getall()
        numbers = response.xpath(
            '//div[@class="products grid"]/a//h2[@class="product-title"]/text()').getall()
        for link, price, number in zip(grid_links, prices, numbers):
            item = WatchesItem()
            item['price'] = price
            item['product_number'] = number.strip()
            item['sku'] = number.strip().replace('.', '').lower() + 'tt'
            if item.get('price') == 'NULL' or not item.get('price'):
                self.logger.warning('Skipping item, EMPTY price {}'.format(item['product_number']))
                yield None
            else:
                yield response.follow(link, callback=self.parse_watch, meta={'item': item})

    def parse_watch(self, response):
        """watch content processing method"""
        item = response.meta['item']
        item['url'] = response.url
        name = response.xpath('//h1[@class="page-title"]/text()').get()
        if name:
            item['name'] = name.upper()
            for i in WatchAttributes.watch_series:
                if i in item['name']:
                    item['series'] = i
                    item['model'] = item['name'].replace(i, '').strip()
            if not item.get('series'):
                customization_text = response.xpath('//section'
                                                    '[contains(translate(@data-title, "ABCDEFGHIJKLMNOPURSTUWXYZ",'
                                                    '"abcdefghijklmnopurstuwxyz"), "customization")]//text()').getall()
                if customization_text:
                    customization_text = ''.join(x for x in customization_text)
                    collection = re.search(r'The([\s\w]+)Collection', customization_text)
                    if collection:
                        item['series'] = collection.group(1).strip().upper()
                        item['model'] = item['name']
                else:
                    item['model'] = item['name']

            item['url_key'] = re.search(r'\/([a-z\-\d]+$)', response.url).group(1)
            item['image_urls'] = response.xpath('//div[@class="js-image-modal"]/img/@src').getall()

            short_description_text = response.xpath('//section[contains(@data-title, "Story") or '
                                                    'contains(@data-title, "STORY")]'
                                                    '//div[@class="content-container"]/p/text()').getall()
            short_description_1paragraph = ' '.join('<p>' + x.strip() + '</p>' for x in short_description_text[:-1])
            short_description_list = '\n'.join('<li>' + x.strip() + '</li>' for x in
                                               response.xpath('//section[contains'
                                                              '(translate(@data-title, "ABCDEFGHIJKLMNOPURSTUWXYZ",'
                                                              '"abcdefghijklmnopurstuwxyz"), "at a glance")]'
                                                              '//div[@class="content-container"]/p/text()').getall())
            item['short_description'] = '<h3 style="text-align: center;"><strong>DESCRIPTION:</strong></h3>' \
                                        + short_description_1paragraph + '<ul>' + short_description_list + '</ul>'

            raw_desc_body = ' '.join(x.strip() for x in response.xpath('//section'
                                                                       '[@class="layout-timepiece-specifications"]'
                                                                       '//div[@class="content-container"]'
                                                                       '//text()').getall())
            if raw_desc_body:
                self.parse_specs(raw_desc_body, item)

            desc_body = response.xpath('//section[@class="layout-timepiece-specifications"]'
                                       '//div[@class="content-container"]').get()
            if desc_body:
                cut_raw_desc_body = re.search(r'((<strong>)?movement[\s\w\W]+)<\/div>', desc_body, re.IGNORECASE)
                if cut_raw_desc_body:
                    item['description'] = '<h3 style="text-align: center;">TECHNICAL SPECIFICATIONS</h3>' \
                                          + cut_raw_desc_body.group(1)
            item['weight'] = 1
            if any(collection.lower() in item['name'].lower() for collection in WatchAttributes.always_available) and \
                    item.get('price'):
                item['quantity'] = 1000
            else:
                item['quantity'] = 0
            item['meta_title'] = 'Buy Jacob&Co, ' + item['name'] + ' with crypto'
            item['meta_description'] = WatchAttributes.meta_description

            yield item
        else:
            self.logger.warning('Skipping Item content NOT valid {}'.format(response.url))
            yield None

    def parse_specs(self, text, model):
        """this method provides parsing plain text specification to extract extra attributes for the item"""
        waterproof = re.search(r'Water[a-z\s:]+(\d+)', text)
        if waterproof:
            model['waterresistance'] = waterproof.group(1) + 'm'

        braclet = re.search(r'STRAP [&|\w]+ CLASP:(.+)', text, re.IGNORECASE)
        if braclet:
            braclet_text = braclet.group(1).strip().lower()
            braclet_text = braclet_text.replace('strap', '').strip()
            braclet_material = re.search(r'\w+', braclet_text)
            if braclet_material:
                model['braclet_material'] = braclet_material.group()

        case = re.search(r'Case:\s+.+', text, re.IGNORECASE)
        if case:
            case = case.group()
            case_material = re.findall(r'([\w:\s\(\)≈\.]+)', case, re.IGNORECASE)
            if case_material:
                case_material = re.sub(r'Material:', '', case_material[2], re.IGNORECASE)
                model['case_material'] = case_material

            diameter = re.search(r'[Diametr:]?\s+(\d+m*)', case, re.IGNORECASE)
            if diameter:
                model['bodydiameter'] = diameter.group(1)

        color_text = re.search(r'(?:Dial|DIAL)[\s\/&|\w]*?:(.+)', text)
        if color_text:
            color_text = color_text.group(1).strip().lower()
            remove_dial_begining = re.sub(r'^(?:[\s\/&|\w]+)?dial:', '', color_text).strip()
            dial_color = re.match(r'^[\w\s-]+', remove_dial_begining)
            if dial_color:
                model['colorofthedial'] = dial_color.group().replace('dial', '').strip()
