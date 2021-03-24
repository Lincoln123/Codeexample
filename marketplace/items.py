# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class WatchesItem(scrapy.Item):
    sku = scrapy.Field()
    product_number = scrapy.Field()
    name = scrapy.Field()
    price = scrapy.Field()
    url_key = scrapy.Field()
    description = scrapy.Field()
    short_description = scrapy.Field()
    meta_title = scrapy.Field()
    meta_description = scrapy.Field()
    images = scrapy.Field()
    image_urls = scrapy.Field()
    weight = scrapy.Field()
    quantity = scrapy.Field()
    url = scrapy.Field()
    braclet_material = scrapy.Field()
    case_material = scrapy.Field()
    waterresistance = scrapy.Field()
    colorofthedial = scrapy.Field()
    bodydiameter = scrapy.Field()
    model = scrapy.Field()
    series = scrapy.Field()
