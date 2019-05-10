from webpage import WebPage
from time import sleep
import re
import csv
from pathlib import Path
from urllib.request import urlretrieve
import os
from random import randint

class ImageCrawl:

    def __enter__(self):
        return self

    def __init__(self):
        self.id=0
        self.urlDict={
            'gettyimages':'https://www.gettyimages.in/photos/',
            'picsearch':'https://www.picsearch.com/index.cgi?q=',
            'bing':'https://www.bing.com/images/search?q=', #key+word       
        }
        self.xpathDict={
            "gettyimages":"//figure[@class='gallery-mosaic-asset__figure']//img",
            "bing":"//div[@class='img_cont hoff']//img",
            "picsearch":"//span[@class='result']//img",
        }
        self.w=WebPage(url=None,browser='chrome')
    
    def nextPage(self,site):
        site=str(site)
        if site=='bing':
            self.w.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        elif site=='picsearch': 
            self.w.driver.find_element_by_xpath("//div//a[@id='nextPage']").click()
        elif site=='gettyimages':
            elem=self.w.driver.find_element_by_xpath("//a[@class='search-pagination__button search-pagination__button--next']")
            url=elem.get_attribute('href')
            print("getty image next page url -------------->",url)
            self.w.driver.get(url)
    
    def imgDownloader(self,imageElems,folderPath):
        for imgEle in imageElems:
            try:
                url=str(imgEle.get_attribute('src'))
                print(url)
                filename=str(re.sub(r'\W+', '', url.split('?')[1]))[:-15]
                print(filename)
                if not os.path.exists(folderPath):
                    os.makedirs(folderPath)
                filepath=Path(folderPath+'/'+filename+'.jpg')
                if not filepath.is_file():
                    urlretrieve(str(url),filepath)
            except Exception as e:
                print(e)
        
    def hispanicStartCrawl(self):
        makeKeyword = lambda string : string.lstrip().replace(' ','+')
        keywords=[]
        with open('keywordlist.csv','r') as a:
            reader=csv.reader(a,delimiter=',')
            for r in reader:
                for text in r:
                    keywords.append(makeKeyword(text.lower()))
            print(keywords)
        for key in self.urlDict:
            for keyword in keywords:
                folderPath=str(Path().absolute())+'/hispanic/'+keyword
                print(folderPath)    
                self.w.driver.get(self.urlDict[key]+keyword)
                if key=='bing':
                    for i in range(0,4): #page load for bing
                        self.nextPage(key)
                sleep(1)
                imageElems = self.w.driver.find_elements_by_xpath(self.xpathDict[key])
                print(imageElems)
                if not key=='bing':
                    for a in range(0,4): #page traverse number
                        self.imgDownloader(imageElems,folderPath)
                        self.nextPage(key)
                        imageElems = self.w.driver.find_elements_by_xpath(self.xpathDict[key])

    
    def blackStartCrawl(self):
        pass

                    

    def __exit__(self,exception_type, exception_value, traceback):
        print("quiting driver.................")
        self.w.driver.quit()

if __name__=='__main__':

    with ImageCrawl() as im:
        im.hispanicStartCrawl()
