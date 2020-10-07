import requests
import csv
import pandas as pd
import os

# Get Trello Token and Trello Key from environment variables set in .bash_profile
key = os.environ.get('TRELLO_KEY')
token = os.environ.get('TRELLO_TOKEN')

# Authentication via Trello API to get the field names
paramsField = (
    ('fields', 'name'),
    ('customFieldItems', 'true'),
    ('key', key),
    ('token', token)
)

params = (('key', key),
          ('token', token))


# Get content of all Column Cards in JSON Format for a given Column
def accessColumnCards(columnId, params=paramsField):
    columnUrl = ''.join(['https://api.trello.com/1/lists/', columnId, '/cards/'])
    responseDoneList = requests.get(columnUrl, params=params)
    columnCardsJSon = responseDoneList.json()
    return columnCardsJSon


# Filter Cards of a Column and only return Cards in which the given fieldId was set
def filterCardsByCustomField(fieldId, cardsJson):
    filteredCardsDic = {}
    for i in cardsJson:
        name = i['name']
        for j in i['customFieldItems']:
            if j['idCustomField'] == fieldId:
                filteredCardsDic[name] = j['value']['number']

    return filteredCardsDic


# Get all CustomFields defined for a Board
def accessCustomFields(boardId):
    boardUrl = ''.join(['https://api.trello.com/1/boards/', boardId, '/customFields'])
    fieldResponse = requests.get(boardUrl, params=paramsField)
    fieldsJson = fieldResponse.json()

    customFieldDic = {}
    customFieldValueDic = {}

    # Get Translation Dictionary from Ids for Field Values of Field Entries
    for i in fieldsJson:
        name = i['name']
        ids = i['id']
        customFieldDic[ids] = name
        if 'options' in i:
            options = i['options']
            for j in options:
                ids = j['id']
                values = j['value']
                for key, value in values.items():
                    customFieldValueDic[ids] = value

    return customFieldDic, customFieldValueDic


# Get a dictionary hosting all Label Id and values for a given board
def accessBoardLabels(boardId):
    boardUrl = ''.join(['https://api.trello.com/1/boards/', boardId, '/labels'])
    labelResponse = requests.get(boardUrl, params=params)
    labelJson = labelResponse.json()
    print(labelJson)
    labelDic = {}

    for i in labelJson:
        name = i['name']
        ids = i['id']
        labelDic[name] = ids

    return labelDic


# Access Column and retrieve the information stored on a card and in its CustomFields
def getColumnWithAllFields(boardId, columnId):
    cardsJson = accessColumnCards(columnId, paramsField)
    columnDic = {}
    customFieldDic, customFieldValueDic = accessCustomFields(boardId)
    for i in cardsJson:

        cardDic = {}
        # Get Card Name
        name = i['name']
        # Get Custom Field Code
        customFieldItems = i['customFieldItems']
        for j in customFieldItems:
            currentIDCustomFieldCode = j['idCustomField']
            # Get Custom Field Name by Code Conversion with Dictionary
            currentIDCustomFieldName = customFieldDic[currentIDCustomFieldCode]
            # If a Dropdown Menu with selectable values is present in the field it's called idValue in CustomFields
            if 'idValue' in j:
                currentIdValueCustomFieldCode = j['idValue']
                # Get Custom Field Value by Code Conversion with Dictionary
                currentIdValueCustomFieldName = customFieldValueDic[currentIdValueCustomFieldCode]
                currentIdValueCustomField = currentIdValueCustomFieldName
            # If the value is provided by the user through a textfield then it's called value in CustomFields
            elif 'value' in j:
                values = j['value']
                for key, value in values.items():
                    currentIdValueCustomField = value
            cardDic[currentIDCustomFieldName] = currentIdValueCustomField

        columnDic[name] = cardDic

        # Convert Dictionary to Dataframe and write it to CSV
        dataFrame = pd.DataFrame.from_dict(columnDic, orient='index')

    return dataFrame, columnDic


# Generates a dataframe that differentiates the story points for done tasks(labeled with approved in the review
# column) and unfinished tasks
def generateStoryPointsDataFrame(boardId, taskColumnsIds, finishedTaskColumn, storyPointFieldId):
    # Generates Dictionary Hosting the Label id and their corresponding value
    labelDic = accessBoardLabels(boardId)

    # Gather all Tasks, that are labeled with 'approved' in the review column
    finishedTasksCards = accessColumnCards(finishedTaskColumn, params)

    finishedTasks = []
    for i in finishedTasksCards:
        currentLabel = i['idLabels']
        approvedLabel = labelDic['approved']
        if approvedLabel in currentLabel:
            finishedTasks.append(i['name'])

    # Since we want to know how many story points are defined in the current sprint we need to add up the defined
    # values of all 3 columns
    storyPointsDic = {}

    for i in taskColumnsIds:
        currentColumn = accessColumnCards(i)
        foundTasksDic = filterCardsByCustomField(storyPointFieldId, currentColumn)
        storyPointsDic.update(foundTasksDic)
    # Differentiate between finished task cards that are labeled as approved and not approved
    doneDic = {}
    notDoneDic = {}
    # Check if The current Task is labeled as approved or not and add it with the story points
    # to the corresponding dictionary
    for key, value in storyPointsDic.items():
        if key in finishedTasks:
            doneDic[key] = value
            notDoneDic[key] = ""
        else:
            doneDic[key] = ""
            notDoneDic[key] = value
    # Create DataFrame hosting all Tasks and Story Points
    storyPointsDataFrame = pd.DataFrame.from_dict(storyPointsDic, columns=["Story Points"], orient='index')
    # Add Columns for Done and Unfinished Tasks
    storyPointsDataFrame['Done'] = doneDic.values()
    storyPointsDataFrame['Not Done'] = notDoneDic.values()
    # Add Title to Index
    storyPointsDataFrame.rename_axis("Task/StoryPoints", axis='index', inplace=True)

    return storyPointsDataFrame


# Write Dictionary locally to CSV File.
def writeToCSV(taskDic, csvName):
    with open(csvName + '.csv', 'w') as output:
        writer = csv.writer(output)
        for key, value in taskDic.items():
            writer.writerow([key, value])


def main():
    # Id List of a Board and its relevant Columns
    boardId = 'Qt98t0nJ'
    sprintBacklogColumnId = '5e184a4bee152d1e2f34e434'
    doingColumnId = '5e184a57eacbcf7d33c1f968'
    reviewColumnId = '5e184a61cf27ab269be3c26b'
    # Id of Custom StoryPoint Field
    fieldStoryPointId = '5e5f7addad92130e3f2dbd60'

    # Get all Cards from the Done Column and store them in a CSV File
    doneColumnId = '5e184a4648a22f2692e637ab'
    taskColumns = [sprintBacklogColumnId, doingColumnId, reviewColumnId]
    columnDataFrame, _ = getColumnWithAllFields(boardId, doneColumnId)
    columnDataFrame.to_csv('FinishedTasks.csv', index=True)
    # Generate Story Points Dataframe and csv for tracking
    storyPointsDataFrame = generateStoryPointsDataFrame(boardId, taskColumns, reviewColumnId, fieldStoryPointId)
    storyPointsDataFrame.to_csv("StoryPoints.csv", index=True)


if __name__ == "__main__":
    main()
