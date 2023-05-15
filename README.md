<p align="center"><img src="logo.png" alt="original" width="100%" height="100%"></p>

<h1 align="center">Welcome to Scrapy-Arweave</h1>
<p>
  <img alt="Version" src="https://img.shields.io/badge/version-0.0.1-blue.svg?cacheSeconds=2592000" />
</p>

Scrapy is a popular open-source and collaborative python framework for extracting the data you need from websites. scrapy-arweave provides scrapy pipelines and feed exports to store items into [Arweave](https://arweave.org/).

### 🏠 [Homepage](https://github.com/pawanpaudel93/scrapy-arweave)

## Install

```shell
pip install scrapy-arweave
```

## Example

[scrapy-arweave-example](https://github.com/pawanpaudel93/scrapy-arweave-example)

## Usage

1. Install scrapy-arweave.

 ```shell
 pip install scrapy-arweave

 ```

2. Add 'scrapy-arweave.pipelines.ImagesPipeline' and/or 'scrapy-arweave.pipelines.FilesPipeline' to ITEM_PIPELINES setting in your Scrapy project if you need to store images or other files to Arweave.
 For Images Pipeline, use:

 ```shell
 ITEM_PIPELINES = {'scrapy_arweave.pipelines.ImagesPipeline': 1}
 ```

 For Files Pipeline, use:

 ```shell
 ITEM_PIPELINES = {'scrapy_arweave.pipelines.FilesPipeline': 1}
 ```

 The advantage of using the ImagesPipeline for image files is that you can configure some extra functions like generating thumbnails and filtering the images based on their size.

 Or You can also use both the Files and Images Pipeline at the same time.

 ```python
 ITEM_PIPELINES = {
  'scrapy_arweave.pipelines.ImagesPipeline': 1,
  'scrapy-arweave.pipelines.FilesPipeline': 1
 }
 ```

 If you are using the ImagesPipeline make sure to install the pillow package. The Images Pipeline requires Pillow 7.1.0 or greater. It is used for thumbnailing and normalizing images to JPEG/RGB format.

 ```shell
 pip install pillow
 ```

 Then, configure the target storage setting to a valid value that will be used for storing the downloaded images. Otherwise the pipeline will remain disabled, even if you include it in the ITEM_PIPELINES setting.

 Add store path of files or images for Web3Storage, LightHouse, Moralis, Pinata or Estuary as required.

 ```python
 # for ImagesPipeline
 IMAGES_STORE = 'arweave://images'
 
 # For FilesPipeline
 FILES_STORE = 'arweave://files'
 ```

 For more info regarding ImagesPipeline and FilesPipline. [See here](https://docs.scrapy.org/en/latest/topics/media-pipeline.html)

3. For Feed storage to store the output of scraping as json, csv, json, jsonlines, jsonl, jl, csv, xml, marshal, pickle etc set FEED_STORAGES as following for the desired output format:

 ```python
 from scrapy_arweave.feedexport import get_feed_storages
 FEED_STORAGES = get_feed_storages()
 ```

 Then set WALLET_JWK and GATEWAY_URL. And, set FEEDS as following to finally store the scraped data.

 ```python
 WALLET_JWK = "<WALLET_JWK>" # It can be wallet file path or jwk data
 GATEWAY_URL = "https://arweave.net"

 FEEDS = {
  'arweave://house.json': {
   "format": "json"
  },
 }
 ```

 See more on FEEDS [here](https://docs.scrapy.org/en/latest/topics/feed-exports.html#feeds)

4. Now perform the scrapping as you would normally.

## Author

👤 **Pawan Paudel**

- Github: [@pawanpaudel93](https://github.com/pawanpaudel93)

## 🤝 Contributing

Contributions, issues and feature requests are welcome!<br />Feel free to check [issues page](https://github.com/pawanpaudel93/scrapy-arweave/issues).

## Show your support

Give a ⭐️ if this project helped you!

Copyright © 2023 [Pawan Paudel](https://github.com/pawanpaudel93).<br />
