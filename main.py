# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 14:20:02 2020

@author: aliha
@twitter: rockingAli5 
"""

import time
import pandas as pd
import json
from bs4 import BeautifulSoup as soup
import re 
from collections import OrderedDict
import datetime
from datetime import datetime as dt
import itertools
import numpy as np
try:
    from tqdm import trange
except ModuleNotFoundError:
    pass

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException


TRANSLATE_DICT = {'Jan': 'Jan',
                 'Feb': 'Feb',
                 'Mac': 'Mar',
                 'Apr': 'Apr',
                 'Mei': 'May',
                 'Jun': 'Jun',
                 'Jul': 'Jul',
                 'Ago': 'Aug',
                 'Sep': 'Sep',
                 'Okt': 'Oct',
                 'Nov': 'Nov',
                 'Des': 'Dec'}

main_url = 'https://1xbet.whoscored.com/'



def getLeagueUrls(minimize_window=True):
    
    driver = webdriver.Chrome('chromedriver.exe')
    
    if minimize_window:
        driver.minimize_window()
        
    driver.get(main_url)
    league_names = []
    league_urls = []
    for i in range(21):
        league_name = driver.find_element_by_xpath('//*[@id="popular-tournaments-list"]/li['+str(i+1)+']/a').text
        league_link = driver.find_element_by_xpath('//*[@id="popular-tournaments-list"]/li['+str(i+1)+']/a').get_attribute('href')
        league_names.append(league_name)
        league_urls.append(league_link)
        
    for link in league_urls:
        if 'Russia' in link:
            r_index = league_urls.index(link)
            
    league_names[r_index] = 'Russian Premier League'
    
    leagues = {}
    for name,link in zip(league_names,league_urls):
        leagues[name] = link
    driver.close()
    return leagues


      
def getMatchUrls(comp_url, season, maximize_window=True):
    
    driver = webdriver.Chrome('chromedriver.exe')
    if maximize_window:
        driver.maximize_window()
    
    # teams = []
    driver.get(comp_url)
    time.sleep(5)
    
    seasons = driver.find_element_by_xpath('//*[@id="seasons"]').get_attribute('innerHTML').split(sep='\n')
    seasons = [i for i in seasons if i]
    
    for i in range(1, len(seasons)+1):
        if driver.find_element_by_xpath('//*[@id="seasons"]/option['+str(i)+']').text == season:
            season = driver.find_element_by_xpath('//*[@id="seasons"]/option['+str(i)+']').click()
    
        
    time.sleep(5)
    fixtures_page = driver.find_element_by_xpath('//*[@id="link-fixtures"]')
    driver.execute_script("arguments[0].scrollIntoView();", fixtures_page)
    driver.execute_script("arguments[0].click();", fixtures_page) 
    time.sleep(5)
    date_config_btn = driver.find_element_by_xpath('//*[@id="date-config-toggle-button"]').click()
    time.sleep(5)
    year1 = driver.find_element_by_xpath('//*[@id="date-config"]/div[1]/div/table/tbody/tr/td[1]/div/table/tbody/tr[1]/td').click()
    selectable_months = driver.find_element_by_xpath('//*[@id="date-config"]/div[1]/div/table/tbody/tr/td[2]/div/table').find_elements_by_class_name("selectable")
    
    n_months = len(selectable_months)
    
    year2 = driver.find_element_by_xpath('//*[@id="date-config"]/div[1]/div/table/tbody/tr/td[1]/div/table/tbody/tr[2]/td').click()
    selectable_months = driver.find_element_by_xpath('//*[@id="date-config"]/div[1]/div/table/tbody/tr/td[2]/div/table').find_elements_by_class_name("selectable")
    
    n_months += len(selectable_months)
    date_config_btn = driver.find_element_by_xpath('//*[@id="date-config-toggle-button"]').click()
    
    match_urls = getFixtureData(driver, n_months)
    
    match_urls = getSortedData(match_urls)
    
    
    driver.close()
    return match_urls


def getTeamUrls(team, match_urls):
    
    team_data = []
    for fixture in match_urls:
        if fixture['home'] == team or fixture['away'] == team:
            team_data.append(fixture)
    team_data = [a[0] for a in itertools.groupby(team_data)]
                
    return team_data


def getMatchesData(match_urls, minimize_window=True):
    
    matches = []
    
    driver = webdriver.Chrome('chromedriver.exe')
    if minimize_window:
        driver.minimize_window()
    
    try:
        for i in trange(len(match_urls), desc='Getting Match Data'):
            match_data = getMatchData(driver, main_url+match_urls[i]['url'], display=False, close_window=False)
            matches.append(match_data)
    except NameError:
        print('Recommended: \'pip install tqdm\' for a progress bar while the data gets scraped....')
        for i in range(len(match_urls)):
            match_data = getMatchData(driver, main_url+match_urls[i]['url'], display=False, close_window=False)
            matches.append(match_data)
    
    driver.close()
    
    return matches




def getFixtureData(driver, n_months):

    matches_ls = []
    for i in range(n_months):
        table_rows = driver.find_elements_by_class_name('divtable-row')
        for row in table_rows:
            match_dict = {}
            element = soup(row.get_attribute('innerHTML'), features='lxml')
            link_tag = element.find("a", {"class":"result-1 rc"})
            if type(link_tag) is type(None):
                date = row.text.split(', ')[-1]
            if type(link_tag) is not type(None):
                match_dict['date'] = date
                match_dict['time'] = element.find('div', {'class':'col12-lg-1 col12-m-1 col12-s-0 col12-xs-0 time divtable-data'}).text
                match_dict['home'] = element.find_all("a", {"class":"team-link"})[0].text
                match_dict['away'] = element.find_all("a", {"class":"team-link"})[1].text
                match_dict['score'] = element.find("a", {"class":"result-1 rc"}).text
                match_dict['url'] = link_tag.get("href")
            matches_ls.append(match_dict)
        prev_month = driver.find_element_by_xpath('//*[@id="date-controller"]/a[1]').click()
        time.sleep(2)
    matches_ls = list(filter(None, matches_ls))

    return matches_ls



def translateDate(data):
    
    for match in data:
        date = match['date'].split()
        match['date'] = ' '.join([TRANSLATE_DICT[date[0]], date[1], date[2]])
    
    return data


def getSortedData(data):

    try:
        data = sorted(data, key = lambda i: dt.strptime(i['date'], '%b %d %Y'))
        return data
    except ValueError:    
        data = translateDate(data)
        data = sorted(data, key = lambda i: dt.strptime(i['date'], '%b %d %Y'))
        return data
    



def getMatchData(driver, url, display=True, close_window=True):
    driver.get(url)

    # get script data from page source
    script_content = driver.find_element_by_xpath('//*[@id="layout-wrapper"]/script[1]').get_attribute('innerHTML')


    # clean script content
    script_content = re.sub(r"[\n\t]*", "", script_content)
    script_content = script_content[script_content.index("matchId"):script_content.rindex("}")]


    # this will give script content in list form 
    script_content_list = list(filter(None, script_content.strip().split(',            ')))
    metadata = script_content_list.pop(1) 


    # string format to json format
    match_data = json.loads(metadata[metadata.index('{'):])
    keys = [item[:item.index(':')].strip() for item in script_content_list]
    values = [item[item.index(':')+1:].strip() for item in script_content_list]
    for key,val in zip(keys, values):
        match_data[key] = json.loads(val)


    # get other details about the match
    region = driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/span[1]').text
    league = driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')[0]
    season = driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')[1]
    if len(driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')) == 2:
        competition_type = 'League'
        competition_stage = ''
    elif len(driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')) == 3:
        competition_type = 'Knock Out'
        competition_stage = driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')[-1]
    else:
        print('Getting more than 3 types of information about the competition.')

    match_data['region'] = region
    match_data['league'] = league
    match_data['season'] = season
    match_data['competitionType'] = competition_type
    match_data['competitionStage'] = competition_stage


    # sort match_data dictionary alphabetically
    match_data = OrderedDict(sorted(match_data.items()))
    match_data = dict(match_data)
    if display:
        print('Region: {}, League: {}, Season: {}, Match Id: {}'.format(region, league, season, match_data['matchId']))
    
    
    if close_window:
        driver.close()
        
    return match_data





def createEventsDF(matches):
    if type(matches) == dict:
        events = matches['events']
        for event in events:
            event.update({'matchId' : matches['matchId'],
                         'startDate' : matches['startDate'],
                         'startTime' : matches['startTime'],
                         'score' : matches['score'],
                         'ftScore' : matches['ftScore'],
                         'htScore' : matches['htScore'],
                         'etScore' : matches['etScore'],
                         'venueName' : matches['venueName'],
                         'maxMinute' : matches['maxMinute']})
        events_df = pd.DataFrame(events)
        return events_df
    else:
        for i in trange(len(matches), desc='Single loop'):
            events = matches[i]['events']
            for event in events:
                event.update({'matchId' : matches[i]['matchId'],
                             'startDate' : matches[i]['startDate'],
                             'startTime' : matches[i]['startTime'],
                             'score' : matches[i]['score'],
                             'ftScore' : matches[i]['ftScore'],
                             'htScore' : matches[i]['htScore'],
                             'etScore' : matches[i]['etScore'],
                             'venueName' : matches[i]['venueName'],
                             'maxMinute' : matches[i]['maxMinute']})
        events_ls = []
        for match in matches:
            match_events = match['events']
            match_events_df = pd.DataFrame(match_events)
            events_ls.append(match_events_df)
                
        events_df = pd.concat(events_ls)
        return events_df
    


def createMatchesDF(data):
    columns_req_ls = ['matchId', 'attendance', 'venueName', 'startTime', 'startDate',
                      'score', 'home', 'away', 'referee']
    matches_df = pd.DataFrame(columns=columns_req_ls)
    if type(data) == dict:
        matches_dict = dict([(key,val) for key,val in data.items() if key in columns_req_ls])
        matches_df = matches_df.append(matches_dict, ignore_index=True)
    else:
        for match in data:
            matches_dict = dict([(key,val) for key,val in match.items() if key in columns_req_ls])
            matches_df = matches_df.append(matches_dict, ignore_index=True)
    
    matches_df = matches_df.set_index('matchId')        
    return matches_df



def load_EPV_grid(fname='EPV_grid.csv'):
    """ load_EPV_grid(fname='EPV_grid.csv')
    
    # load pregenerated EPV surface from file. 
    
    Parameters
    -----------
        fname: filename & path of EPV grid (default is 'EPV_grid.csv' in the curernt directory)
        
    Returns
    -----------
        EPV: The EPV surface (default is a (32,50) grid)
    
    """
    epv = np.loadtxt(fname, delimiter=',')
    return epv






def get_EPV_at_location(position,EPV,attack_direction,field_dimen=(106.,68.)):
    """ get_EPV_at_location
    
    Returns the EPV value at a given (x,y) location
    
    Parameters
    -----------
        position: Tuple containing the (x,y) pitch position
        EPV: tuple Expected Possession value grid (loaded using load_EPV_grid() )
        attack_direction: Sets the attack direction (1: left->right, -1: right->left)
        field_dimen: tuple containing the length and width of the pitch in meters. Default is (106,68)
            
    Returrns
    -----------
        EPV value at input position
        
    """
    
    x,y = position
    if abs(x)>field_dimen[0]/2. or abs(y)>field_dimen[1]/2.:
        return 0.0 # Position is off the field, EPV is zero
    else:
        if attack_direction==-1:
            EPV = np.fliplr(EPV)
        ny,nx = EPV.shape
        dx = field_dimen[0]/float(nx)
        dy = field_dimen[1]/float(ny)
        ix = (x+field_dimen[0]/2.-0.0001)/dx
        iy = (y+field_dimen[1]/2.-0.0001)/dy
        return EPV[int(iy),int(ix)]



                

def to_metric_coordinates_from_whoscored(data,field_dimen=(106.,68.) ):
    '''
    Convert positions from Whoscored units to meters (with origin at centre circle)
    '''
    x_columns = [c for c in data.columns if c[-1].lower()=='x'][:2]
    y_columns = [c for c in data.columns if c[-1].lower()=='y'][:2]
    x_columns_mod = [c+'_metrica' for c in x_columns]
    y_columns_mod = [c+'_metrica' for c in y_columns]
    data[x_columns_mod] = (data[x_columns]/100*106)-53
    data[y_columns_mod] = (data[y_columns]/100*68)-34
    return data




def addEpvToDataFrame(data):
    
    # loading EPV data
    EPV = load_EPV_grid('EPV_grid.csv')

    # converting opta coordinates to metric coordinates
    data = to_metric_coordinates_from_whoscored(data)
    
    EPV_start = []
    EPV_end = []
    EPV_difference = []
    for i,row in data.iterrows():
        if row['type']['displayName'] == 'Pass' and row['outcomeType']['value'] == 1:
            start_pos = (row['x_metrica'], row['y_metrica'])
            start_epv = get_EPV_at_location(start_pos,EPV,attack_direction=1)
            EPV_start.append(start_epv)
            
            end_pos = (row['endX_metrica'], row['endY_metrica'])
            end_epv = get_EPV_at_location(end_pos,EPV,attack_direction=1)
            EPV_end.append(end_epv)
            
            diff = end_epv - start_epv
            EPV_difference.append(diff)
            
        else:
            EPV_start.append(np.nan)
            EPV_end.append(np.nan)
            EPV_difference.append(np.nan)
    
    data = data.assign(EPV_difference = EPV_difference)
    # dump useless columns
    drop_cols = ['x_metrica', 'endX_metrica', 'y_metrica',
                 'endY_metrica']
    data.drop(drop_cols, axis=1, inplace=True)
    
    return data





def getUnderstatShotData(match_url, driver):
    
    driver.get(match_url)

    # getting shot data from script
    shot_data_tag = driver.find_element_by_xpath('/html/body/div[1]/div[3]/div[2]/div[1]/div/script')
    script_data = shot_data_tag.get_attribute('innerHTML')
    json_data = script_data[script_data.index("('")+2:script_data.index("')")]
    json_data = json_data.encode('utf8').decode('unicode_escape')
    shot_data = json.loads(json_data)
    
    # closing browser window
    driver.close()

    # converting shot data from json to dataframe format
    h_df = pd.DataFrame(shot_data['h'])
    a_df = pd.DataFrame(shot_data['a'])
    shot_data_df = pd.concat([h_df,a_df]).reset_index(drop=True)
    shot_data_df = shot_data_df.astype({'X':'float', 'Y':'float', 'xG':'float'}) 

    # sorting by minute sequence
    shot_data_df = shot_data_df.astype({'minute':int}) 
    shot_data_df = shot_data_df.sort_values('minute')
    
    return shot_data_df






def getxGFromUnderstat(match_data, events_df, driver):
    
    # Opening home page
    url = 'https://understat.com'
    driver.get(url)
    
    
    # Getting leagues available in understat
    und_leagues = driver.find_element_by_xpath('//*[@id="header"]/div/nav[1]/ul').text.split('\n')
    found = False
    for lg in und_leagues:
        if match_data['league'].upper() == ''.join(lg.split()).upper():
            driver.find_element_by_link_text(lg).click()
            found = True
            break
    
    
    # If league not found -> exit
    if found == False:
        print('Expected Goals data for league not available')
        driver.close()
        
    else:
        # Getting seasons available in understat
        season_btn = driver.find_element_by_xpath('//*[@id="header"]/div/div[2]/div').click()
        und_seasons = driver.find_element_by_xpath('//*[@id="header"]/div/div[2]/ul').text.split('\n')
        found = False
        for szn in und_seasons:
            if match_data['season'] == szn:
                i = str(und_seasons.index(szn)+1)
                driver.find_element_by_xpath("//*[@id='header']/div/div[2]/ul/li["+i+"]").click()
                found = True
                break
        
        
        # If season not found -> exit
        if found == False:
            print('Expected Goals data for season not available')
            driver.close()

        else:
            # Getting match date display
            timezn_off_btn = driver.find_element_by_xpath('/html/body/div[1]/div[3]/div[2]/div/div/div[1]/div/label[3]').click()
            date = '-'.join(match_data['startDate'].split('T')[0].split('-')[::-1])
            d = datetime.datetime.strptime(date, '%d-%m-%Y')
            date = datetime.date.strftime(d, "%A, %B %d, %Y")
            prev_btn = driver.find_element_by_xpath('/html/body/div[1]/div[3]/div[2]/div/div/button[1]')
            next_btn = driver.find_element_by_xpath('/html/body/div[1]/div[3]/div[2]/div/div/button[2]')
            btn_ls = []
            found = True
            while found:
                display_dates = [datetime.datetime.strptime(d.text, '%A, %B %d, %Y') for d in driver.find_elements_by_class_name('calendar-date')]
                if d in display_dates:
                    found = False
                elif datetime.datetime(d.year, d.month, d.day) < datetime.datetime(display_dates[0].year, display_dates[0].month, display_dates[0].day):
                    prev_btn.click()
                    btn_ls.append('p')
                else:   
                    next_btn.click()
                    btn_ls.append('n')
                if btn_ls.count('p') != len(btn_ls) and btn_ls.count('n') != len(btn_ls):
                    found = False
                    print('Date not found')


            # Getting match url
            title = match_data['home']['name']+match_data['score']+match_data['away']['name']
            games_on_date = [soup(contain.get_attribute('innerHTML'), features="lxml").find_all('div', {'class':'calendar-game'}) 
                             for contain in driver.find_elements_by_class_name("calendar-date-container") 
                             if contain.text.split('\n')[0]==date][0]
            match_url = [url+'/'+game.find('a', {'class':'match-info'}).get('href') for game in games_on_date 
                         if game.find('div', {'class':'block-home team-home'}).text in match_data['home']['name']
                         and game.find('div', {'class':'block-away team-away'}).text in match_data['away']['name']][0]


            # Addding xG from shot data to events dataframe
            und_shotdata = getUnderstatShotData(match_url, driver)
            events_df['xG'] = np.nan
            und_shotdata.index = events_df.loc[events_df.isShot==True].index
            for i in events_df.loc[events_df.isShot==True].index:
                events_df.loc[[i],'xG'] = und_shotdata.loc[[i],'xG']
    
    
    return events_df







