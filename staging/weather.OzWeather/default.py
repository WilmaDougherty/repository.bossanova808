#to do: fallback images
#skin files into the repo so they get delivered with the add on and installation 


# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
 
import os, sys, urllib, urllib2, socket
import xbmc, xbmcvfs, xbmcgui, xbmcaddon
import CommonFunctions
import re
import ftplib
import shutil
import time
from PIL import Image

# plugin constants
version = "0.2.1"
plugin = "OzWeather-" + version
author = "Bossanova808 (bossanova808@gmail.com)"
url = "www.bossanova808.net"

#parseDOM setup
dbg = False # Set to false if you don't want debugging
dbglevel = 0 # Do NOT change from 3
common = CommonFunctions.CommonFunctions()
common.plugin = plugin

#addon setup
__addon__      = xbmcaddon.Addon()
__provider__   = __addon__.getAddonInfo('name')
__cwd__        = __addon__.getAddonInfo('path')
__resource__   = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
sys.path.append (__resource__)

#import the tables that map conditions to icon number and short days to long days
from utilities import *

#Handy Strings
WEATHER_WINDOW  = xbmcgui.Window(12600)
WeatherZoneURL = 'http://www.weatherzone.com.au'
ftpStub = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar_transparencies/"
radarBackgroundsPath = ""
loopImagesPath = ""


################################################################################
# strip given chararacters from all members of a given list
       
def striplist(l, chars):
    return([x.strip(chars) for x in l])
    
################################################################################
# log messages neatly to the XBMC master log
       
def log(message, inst=None):
    if inst is None: 
      xbmc.log(plugin + ": " + message)
    else:
      xbmc.log(plugin + " Exception: " + message + "[" + str(inst) +"]")
 

################################################################################
#just sets window properties we can refer to later in the MyWeather.xml skin file

def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)

################################################################################
#set the location and radar code properties

def refresh_locations():
    location_set1 = __addon__.getSetting('Location1')
    location_set2 = __addon__.getSetting('Location2')
    location_set3 = __addon__.getSetting('Location3')
    locations = 0
    if location_set1 != '':
        locations += 1
        set_property('Location1', location_set1)
    else:
        set_property('Location1', '')
    if location_set2 != '':
        locations += 1 
        set_property('Location2', location_set2)
    else:
        set_property('Location2', '')
    if location_set3 != '':
        locations += 1
        set_property('Location3', location_set3)
    else:
        set_property('Location3', '')
    set_property('Locations', str(locations))

    radar_set1 = __addon__.getSetting('Radar1')
    radar_set2 = __addon__.getSetting('Radar2')
    radar_set3 = __addon__.getSetting('Radar3')
    radars = 0
    if radar_set1 != '':
        radars += 1
        set_property('Radar1', radar_set1)
    else:
        set_property('Radar1', '')
    if radar_set2 != '':
        radars += 1 
        set_property('Radar2', radar_set2)
    else:
        set_property('Radar2', '')
    if radar_set3 != '':
        radars += 1
        set_property('Radar3', radar_set3)
    else:
        set_property('Radar3', '')
    set_property('Radars', str(locations))


################################################################################
# The main forecast retrieval function
# Does either a basic forecast or a more extended forecast with radar etc.
# if the appropriate setting is set

def forecast(url, radarCode):
    global radarBackgroundsPath, loopImagesPath

    extendedFeatures = __addon__.getSetting('ExtendedFeaturesToggle')
    log("Getting weather from " + url + ", Extended features = " + str(extendedFeatures))  
    data = common._fetchPage({"link":url})
    if data != '':
       propertiesPDOM(data["content"], extendedFeatures)
    #ok now we want to build the radar
    if extendedFeatures == "true":

      #strings to store the paths we will use    
      radarBackgroundsPath = xbmc.translatePath("special://profile/addon_data/weather.ozweather/radarbackgrounds/" + radarCode + "/");
      loopImagesPath = xbmc.translatePath("special://profile/addon_data/weather.ozweather/currentloop/" + radarCode + "/");

      set_property('Radar', "")
      buildImages(radarCode)
      radar = ""
      radar = __addon__.getSetting('Radar%s' % sys.argv[1])
      #set the radar to blank so that xbmc will update radar images with the new set 
      #time.sleep(1)
      set_property('Radar', radar)
      
      #NO LONGER NEEDED
      #reload the skin to force an update for the radar image
      #only do this if we're actually on the weather page
      #nWin = xbmcgui.getCurrentWindowId()
      #if nWin == 12600:
      #  log("OzWeather: Reloading the skin because we're on the weather page")
      #  xbmc.executebuiltin( 'XBMC.ReloadSkin()' )

################################################################################
# Downloads a radar background given a BOM radar code like IDR023 & filename
# Converts the image from indexed colour to RGBA colour 

def downloadBackground(radarCode, fileName):
    global radarBackgroundsPath, loopImagesPath

    #ok get ready to retrieve some images
    image = urllib.URLopener() 

    outFileName = fileName
    
    #the legend file doesn't have the radar code int he filename
    if fileName == "IDR.legend.0.png":
      outFileName = "legend.png"
    else:
      #append the radar code 
      fileName = radarCode + "." + fileName

    #download the backgrounds only if we don't have them yet
    if not xbmcvfs.exists( radarBackgroundsPath + fileName):       
        #the legened image showing the rain scale
        try:
          imageFileIndexed = radarBackgroundsPath + "idx." + fileName
          imageFileRGB = radarBackgroundsPath + outFileName
          image.retrieve(ftpStub + fileName, imageFileIndexed )
          im = Image.open( imageFileIndexed )
          rgbimg = im.convert('RGBA')
          rgbimg.save(imageFileRGB, "PNG")
          os.remove(imageFileIndexed)          
        except Exception as inst:
           xbmc.log("OzWeather: Error, couldn't retrieve " + fileName + " - error: " + str(inst))


def prepareBackgrounds(radarCode):
    global radarBackgroundsPath, loopImagesPath

    downloadBackground(radarCode, "IDR.legend.0.png")
    downloadBackground(radarCode, "background.png")
    downloadBackground(radarCode, "locations.png")
    downloadBackground(radarCode, "range.png")
    downloadBackground(radarCode, "topography.png")
    downloadBackground(radarCode, "catchments.png")
    #downloadBackground(radarCode, "waterways.png")
    #downloadBackground(radarCode, "wthrDistricts.png")
    #downloadBackground(radarCode, "rail.png")
    #downloadBackground(radarCode, "roads.png")



################################################################################
# Builds the radar images given a BOM radar code like IDR023
# the background images are permanently cached (user can manually delete if 
# they need to)
# the radar images are downloaded with each update (~60kb each time)
    
def buildImages(radarCode):   

    #remove the temporary files - we only want fresh radar files
    #this results in maybe ~60k used per update.  
    if xbmcvfs.exists( loopImagesPath ):
      shutil.rmtree( loopImagesPath , ignore_errors=True)      

    #we need make the directories to store stuff if they don't exist
    if not xbmcvfs.exists( radarBackgroundsPath ):
      os.makedirs( radarBackgroundsPath )        
    if not xbmcvfs.exists( loopImagesPath ):
      os.makedirs( loopImagesPath )    
    
    
    prepareBackgrounds(radarCode)        

    #Ok so we have the backgrounds...now it is time get the loop
    #first we retrieve a list of the available files via ftp
    #ok get ready to retrieve some images
    image = urllib.URLopener() 
    files = []

    ftp = ftplib.FTP("ftp.bom.gov.au")
    ftp.login("anonymous", "anonymous@anonymous.org")
    ftp.cwd("/anon/gen/radar/")

    #connected, so let's get the list
    try:
        files = ftp.nlst()
    except ftplib.error_perm, resp:
        if str(resp) == "550 No files found":
            log("No files in BOM ftp directory!")
        else:
            log("Something wrong in the ftp bit of radar images")
            
    #ok now we need just the matching radar files...
    loopPicNames = []    
    for f in files:
        if radarCode in f:
          loopPicNames.append(f)            
  
    #download the actual images, might as well get the longest loop they have
    for f in loopPicNames:
       #ignore the composite gif...
       if f[-3:] == "png":
         imageToRetrieve = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar/" + f
         log("Retrieving radar image: " + imageToRetrieve)
         try:
            image.retrieve(imageToRetrieve, loopImagesPath + "/" + f )
         except Exception as inst:
            log("Failed to retrieve radar image: " + imageToRetrieve + ", oh well never mind!", inst )
            

################################################################################
# this is the main scraper function that uses parseDOM to scrape the 
# data from the weatherzone site.
        
def propertiesPDOM(page, extendedFeatures):

    #manually clear these
    set_property('Day4.OutlookIcon', "")
    set_property('Day5.OutlookIcon', "")
    set_property('Day6.OutlookIcon', "")

    #pull data from the current observations table
    ret = common.parseDOM(page, "div", attrs = { "class": "details_lhs" })
    observations = common.parseDOM(ret, "td", attrs = { "class": "hilite bg_yellow" }) 
    #Observations now looks like - ['18.3&deg;C', '4.7&deg;C', '18.3&deg;C', '41%', 'SSW 38km/h', '48km/h', '1015.7hPa', '-', '0.0mm / -']   
    temperature = str.strip(observations[0], '&deg;C')
    dewPoint = str.strip(observations[1], '&deg;C')
    feelsLike = str.strip(observations[2], '&deg;C')
    humidity = str.strip(observations[3], '%')
    windTemp = observations[4].partition(' ');
    windDirection = windTemp[0]
    windSpeed = str.strip(windTemp[2], 'km/h')
    #there's no UV so we get that from the forecast, see below
 
    #pull the basic data from the forecast table  
    ret = common.parseDOM(page, "div", attrs = { "class": "boxed_blue_nopad" })
    #create lists of each of the maxes, mins, and descriptions
    #Get the days UV in text form like 'Extreme' and number '11'
    UVchunk = common.parseDOM(ret, "td", attrs = { "style": "text-align: center;" })
    UVtext = common.parseDOM(UVchunk, "span")
    UVnumber = common.parseDOM(UVchunk, "span", ret = "title")
    UV = UVtext[0] + ' (' + UVnumber[0] + ')'
    #get the 7 day max min forecasts
    maxMin = common.parseDOM(ret, "td")
    #for count, element in enumerate(maxMin):
    #   print "********" , count , "^^^" , str(element)
    maxList = striplist(maxMin[7:14],'&deg;C');
    minList = striplist(maxMin[14:21],'&deg;C');
    #and the short forecasts
    shortDesc = common.parseDOM(ret, "td", attrs = { "class": "bg_yellow" })
    shortDesc = common.parseDOM(ret, "span", attrs = { "style": "font-size: 0.9em;" })
    shortDesc = shortDesc[0:7]
          
    for count, desc in enumerate(shortDesc):
      shortDesc[count] = str.replace(shortDesc[count], '-<br />','')

    #log the collected data, helpful for finding errors
    #log("Collected data: shortDesc [" + str(shortDesc) + "] maxList [" + str(maxList) +"] minList [" + str(minList) + "]")
    
    #and the names of the days
    days = common.parseDOM(ret, "span", attrs = { "style": "font-size: larger;" })
    days = common.parseDOM(ret, "span", attrs = { "class": "bold" })
    days = days[0:7]
    for count, day in enumerate(days):
        days[count] = DAYS[day]
 
    #get the longer current forecast for the day
    # or just use the short one if this is disabled in settings
    if extendedFeatures == "true":
        longDayCast = common.parseDOM(page, "div", attrs = { "class": "top_left" })
        #print '@@@@@@@@@ Long 1', longDayCast
        longDayCast = common.parseDOM(longDayCast, "p" )
        #print '@@@@@@@@@ Long 2', longDayCast
        #new method - just strip the crap (e.g. tabs) out of the string and use a colon separator for the 'return' as we don't have much space
        longDayCast = common.stripTags(longDayCast[0])
        #print longDayCast       
        longDayCast = str.replace(longDayCast, '\t','')
        longDayCast = str.replace(longDayCast, '\r',' ')
        longDayCast = str.replace(longDayCast, '&amp;','&')
        #print '@@@@@@@@@ Long 4', longDayCast    
        longDayCast = longDayCast[:-1]
        #print '@@@@@@@@@@@@@@@@' , longDayCast[-5:]
        #if longDayCast[-5:] != "winds":
        #  longDayCast = longDayCast + " fire danger."    
    else:
        longDayCast = shortDesc[0]
 
    #if for some reason the codes change return a neat 'na' response
    try:
        weathercode = WEATHER_CODES[shortDesc[0]]   
    except:
        weathercode = 'na'
  
    # set all the XBMC window properties.
    # wrap it in a try: in case something goes wrong, it's better than crashing out...
    
    try:
      #now set all the XBMC current weather properties
      set_property('Current.Condition'     , shortDesc[0])
      set_property('Current.ConditionLong' , longDayCast)    
      set_property('Current.Temperature'   , temperature)
      set_property('Current.Wind'          , windSpeed)
      set_property('Current.WindDirection' , windDirection)
      set_property('Current.Humidity'      , humidity)
      set_property('Current.FeelsLike'     , feelsLike)
      set_property('Current.DewPoint'      , dewPoint)
      set_property('Current.UVIndex'       , UV)
      set_property('Current.OutlookIcon'   , '%s.png' % weathercode)
      set_property('Current.FanartCode'    , weathercode)
  
      #and all the properties for the forecast
      for count, desc in enumerate(shortDesc):
          try:
              weathercode = WEATHER_CODES[shortDesc[count]]
          except:
              weathercode = 'na'
          
          day = days[count]
          set_property('Day%i.Title'       % count, day)
          set_property('Day%i.HighTemp'    % count, maxList[count])
          set_property('Day%i.LowTemp'     % count, minList[count])
          set_property('Day%i.Outlook'     % count, desc)
          set_property('Day%i.OutlookIcon' % count, '%s.png' % weathercode)
          set_property('Day%i.FanartCode'  % count, weathercode)
      
    except Exception as inst:
      log("********** OzWeather Couldn't set all the properties, sorry!!", inst)
    
    #We're done
    


##############################################
### NOW ACTUALLTY RUN THIS PUPPY - this is main() in the old language...    

socket.setdefaulttimeout(10)      

#the being called from the settings section where the user enters their postcodes    
if sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', 'Enter your 4 digit postcode e.g. 3000', False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText() != ''):
        text = keyboard.getText()

        #need to submit the postcode to the weatherzone search
        searchURL = 'http://weatherzone.com.au/search/'
        user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
        host = 'www.weatherzone.com.au'
        headers = { 'User-Agent' : user_agent, 'Host' : host }
        values = {'q' : text, 't' : '3' }
        data = urllib.urlencode(values)
        req = urllib2.Request(searchURL, data, headers)
        response = urllib2.urlopen(req)
        resultPage = str(response.read())
        #was there only one match?  If so it returns the page for that match so we need to check the URL
        responseurl = response.geturl()
        if responseurl != 'http://weatherzone.com.au/search/':
            #we were redirected to an actual result page
            locationName = common.parseDOM(resultPage, "h1", attrs = { "class": "unenclosed" })
            locationName = str.split(locationName[0], ' Weather')
            locations = [locationName[0] + ', ' + text]
            locationids = [responseurl]
        else:        
            #we got back a page to choose a more specific location
            skimmed = common.parseDOM(resultPage, "ul", attrs = { "class": "typ2" })
            #ok now get two lists - one of the friendly names
            #and a matchin one of the URLs to store
            locations = common.parseDOM(skimmed[0], "a")
            templocs = common.parseDOM(skimmed[0], "a", ret="href")
            #build the full urls
            locationids = []
            for count, loc in enumerate(templocs):
                locationids.append(WeatherZoneURL + loc)
            #if we did not get enough data back there are no locations with this postcode 
            if len(skimmed)<=1:
                locations = []
                locationids = []
      
        #now get them to choose an actual location
        dialog = xbmcgui.Dialog()
        if locations != []:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1: 
                __addon__.setSetting(sys.argv[1], locations[selected])
                __addon__.setSetting(sys.argv[1] + 'id', locationids[selected])
        else:
            dialog.ok(__provider__, xbmc.getLocalizedString(284))


#script is being called in general use, not from the settings page            
#get the currently selected location and grab it's forecast
else:
    
    #TODO - MESSAGE ON FIRST RUN??
    #is this the first run?  If so, let's show a message and then record we've run this.
    #runOnceToken =  xbmc.translatePath("special://profile/addon_data/weather.ozweather/" ) + "RunOnceToken"
    #if not xbmcvfs.exists( runOnceToken ):
    #  open(runOnceToken, 'w').close() 
      

    #retrieve the currently set location & radar
    location = ""
    location = __addon__.getSetting('Location%sid' % sys.argv[1])
    radar = ""
    radar = __addon__.getSetting('Radar%s' % sys.argv[1])
    #set the radar name to a property to we can use it to title the window
    set_property('Radar', radar)
    #now get a forecast
    forecast(location, radar)

#refressh the locations and set the weather provider property
refresh_locations()
set_property('WeatherProvider', 'BOM Australia via WeatherZone')

