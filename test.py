# import relevant functions 
from main import getLeagueUrls, getMatchUrls, getTeamUrls, getMatchesData, getMatchData, createEventsDF, createMatchesDF, addEpvToDataFrame

# import relevant variables
from main import main_url

# import relevant packages
import pandas as pd

from selenium import webdriver 
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])




# write test functions for all functions in file
def test():
    print('Testing getLeagueUrls function...')
    leagues = getLeagueUrls()
    assert type(leagues) == dict
    assert len(leagues) == 23
    print('getLeagueUrls function passed all tests.')
    
    print('Testing getMatchUrls function...')
    comp_urls = getLeagueUrls()
    match_urls = getMatchUrls(comp_urls, 'Premier League', '2019/2020')
    assert type(match_urls) == list
    assert len(match_urls) == 380
    print('getMatchUrls function passed all tests.')
    
    print('Testing getTeamUrls function...')
    team_urls = getTeamUrls('Liverpool', match_urls)
    assert type(team_urls) == list
    assert len(team_urls) == 38
    print('getTeamUrls function passed all tests.')
    
    print('Testing getMatchesData function...')
    matches = getMatchesData(team_urls)
    assert type(matches) == list
    assert len(matches) == 38
    print('getMatchesData function passed all tests.')
    
    print('Testing getMatchData function...')
    driver = webdriver.Chrome('drivers/chromedriver.exe', options=options)
    match_data = getMatchData(driver, main_url+'/Matches/1375927/Live/England-Premier-League-2019-2020-Liverpool-Norwich')
    assert type(match_data) == dict
    assert len(match_data) == 36
    print('getMatchData function passed all tests.')
    
    print('Testing createEventsDF function...')
    events_df = createEventsDF(match_data)
    assert type(events_df) == pd.core.frame.DataFrame
    assert events_df.shape[1] == 259
    print('createEventsDF function passed all tests.')
    
    print('Testing createMatchesDF function...')
    matches_df = createMatchesDF(match_data)
    assert type(matches_df) == pd.core.frame.DataFrame
    assert matches_df.shape[1] == 8
    print('createMatchesDF function passed all tests.')
    
    print('Testing addEpvToDataFrame function...')
    events_df = addEpvToDataFrame(events_df)
    assert type(events_df) == pd.core.frame.DataFrame
    assert events_df.shape[1] == 260
    print('addEpvToDataFrame function passed all tests.')
    
    print('All tests passed.')  

if __name__ == '__main__':
    test()
    


