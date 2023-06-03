import telebot
from telebot import util
import os
import pandas as pd
from datetime import datetime, timedelta
import time
import dropbox
from github import Github
#! TOKEN = ""
#! DROPBOXTOKEN = ""
#! GITHUBTOKEN = ""
#! admin_user_name = ""
bot = telebot.TeleBot(TOKEN)
# dbx = dropbox.Dropbox(DROPBOXTOKEN)
inputcsvname = 'students.csv'
outputcsvname = 'schedule.csv'

github = Github(GITHUBTOKEN)
repository = github.get_user().get_repo('Backup')


studentsfile = pd.read_csv(inputcsvname)

try:
    gitfile = repository.get_contents(outputcsvname)
    # dbx.files_download_to_file(outputcsvname, '/' + outputcsvname)
    with open(outputcsvname, 'wb') as new_file:
        new_file.write(gitfile.decoded_content)
except Exception as e:
    print(e)

if not os.path.exists(outputcsvname):
    open(outputcsvname, 'w').close()
fieldnames = ['name', 'number', 'time']
try:
    schedulefile = pd.read_csv(outputcsvname)
except pd.errors.EmptyDataError:
    schedulefile = pd.DataFrame(columns=fieldnames)

studentsfile['number'] = studentsfile['number'].astype(int)
schedulefile['number'] = schedulefile['number'].astype(int)

Startingtime = datetime(2022, 5, 8, 10, 0, 0)


def swap(df, num1, num2):
    i1, i2 = df[df['number'] ==
                num1].index[0], df[df['number'] == num2].index[0]
    a, b = df.iloc[i1, :].copy(), df.iloc[i2, :].copy()
    temp = a['time']
    a['time'] = b['time']
    b['time'] = temp
    df.iloc[i1, :], df.iloc[i2, :] = b, a
    # df = df.sort_index()
    return df


def nextDate(Date):
    if(Date == datetime(2022, 5, 8, 13, 0, 0)):
        return datetime(2022, 5, 10, 11, 30, 0)
    else:
        return Date + timedelta(minutes=5)


def getCurrentTime():
    global schedulefile
    if(schedulefile.empty):
        time = Startingtime
    else:
        lastrow = schedulefile.iloc[-1]
        time = datetime.strptime(
            lastrow.time, '%d/%m/%y %H:%M')
        time = nextDate(time)
    return time


def addStudenttoSchedule(name, number):
    global schedulefile
    if(schedulefile.empty):
        time = Startingtime
    else:
        lastrow = schedulefile.iloc[-1]
        time = datetime.strptime(
            lastrow.time, '%d/%m/%y %H:%M')
        time = nextDate(time)
    newrow = pd.DataFrame.from_records(
        [{'name': name, 'number': number, 'time': time.strftime('%d/%m/%y %H:%M')}])
    schedulefile = pd.concat([schedulefile, newrow], ignore_index=True)
    schedulefile.to_csv(outputcsvname, index=False)
    f = open(outputcsvname, 'rb')
    # dbx.files_upload(f.read(), "/"+outputcsvname, mute=True,
    #                  mode=dropbox.files.WriteMode.overwrite)
    sha = repository.get_contents(outputcsvname).sha
    repository.update_file(
        outputcsvname, "create_file via PyGithub", f.read(), sha)


def verifySchedule(message, number):
    if(message.text == '/yes'):
        srow = studentsfile[studentsfile['number'] == number]
        addStudenttoSchedule(srow['name'].values[0], number)
        row = schedulefile[schedulefile['number'] == number]
        bot.reply_to(message, "Your number is scheduled for " +
                     row['time'].values[0])
    # global schedulefile
    # if(schedulefile.empty):
    #     time = Startingtime
    # else:
    #     lastrow = schedulefile.iloc[-1]
    #     time = datetime.strptime(
    #         lastrow.time, '%d/%m/%y %H:%M')
    #     time = nextDate(time)


def forceaddstep(message):
    global schedulefile
    text = message.text.split(',')
    try:
        newrow = pd.DataFrame.from_records(
            [{'name': text[0], 'number': int(text[1]), 'time': getCurrentTime().strftime('%d/%m/%y %H:%M')}])
        schedulefile = pd.concat([schedulefile, newrow], ignore_index=True)
        schedulefile.to_csv(outputcsvname, index=False)
        f = open(outputcsvname, 'rb')
        sha = repository.get_contents(outputcsvname).sha
        repository.update_file(
            outputcsvname, "create_file via PyGithub", f.read(), sha)
        bot.reply_to(message, "done")
    except ValueError:
        bot.reply_to(message, "Please enter a valid number!!")


def swapstep(message):
    global schedulefile
    text = message.text.split(',')
    try:
        schedulefile = swap(schedulefile, int(text[0]), int(text[1]))
        schedulefile.to_csv(outputcsvname, index=False)
        f = open(outputcsvname, 'rb')
        sha = repository.get_contents(outputcsvname).sha
        repository.update_file(
            outputcsvname, "create_file via PyGithub", f.read(), sha)
        bot.reply_to(message, "done")
    except ValueError:
        bot.reply_to(message, "Please enter a valid number")


def restorecsvstep(message):
    global schedulefile
    file_name = message.document.file_name
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(outputcsvname, 'wb') as new_file:
        new_file.write(downloaded_file)
    schedulefile = pd.read_csv(file_name)
    f = open(outputcsvname, 'rb')
    sha = repository.get_contents(outputcsvname).sha
    repository.update_file(
        outputcsvname, "create_file via PyGithub", f.read(), sha)
    bot.reply_to(message, "done")


@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "Howdy, how are you doing? " +
                 message.chat.first_name + " " + message.chat.last_name)


# chat_id checks id corresponds to your list or not.
@bot.message_handler(commands=['reset'])
def reset(message):
    if(message.chat.username == admin_user_name):
        global schedulefile
        schedulefile = pd.DataFrame(columns=fieldnames)
        schedulefile.to_csv(outputcsvname, index=False)
        f = open(outputcsvname, 'rb')
        sha = repository.get_contents(outputcsvname).sha
        repository.update_file(
            outputcsvname, "create_file via PyGithub", f.read(), sha)
        bot.reply_to(message, "Reset")
    else:
        bot.send_message(
            message.chat.id, "You are not allowed to use this command.")


@bot.message_handler(regexp="[0-9]{9}")
def handle_message(message):
    number = int(message.text)
    srow = studentsfile[studentsfile['number'] == number]
    row = schedulefile[schedulefile['number'] == number]
    if(srow.empty):
        bot.reply_to(
            message, "You are not in the list. Please contact the admin.")
        return
    if(not row.empty):
        bot.reply_to(message, "Your number is already in the schedule.")
        bot.reply_to(message, "Your number is scheduled for " +
                     row['time'].values[0])
    else:
        msg = bot.reply_to(message, "Your name is " + srow['name'].values[0] +
                           " and next availble time is " + getCurrentTime().strftime('%d/%m/%y %H:%M') + " are you sure you want to continue /yes or /no ?")
        bot.register_next_step_handler(
            msg, lambda x: verifySchedule(x, number))
        # addStudenttoSchedule(srow['name'].values[0], number)
        # row = schedulefile[schedulefile['number'] == number]


@bot.message_handler(commands=['report'])
def report(message):
    global schedulefile
    if(schedulefile.empty):
        bot.reply_to(message, "No one has been scheduled until now.")
    else:
        large_text = schedulefile.to_string()
        splitted_text = util.smart_split(large_text, chars_per_string=3000)
        for text in splitted_text:
            bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['reportcsv'])
def reportcsv(message):
    global schedulefile
    if(schedulefile.empty):
        bot.reply_to(message, "No one is scheduled for now.")
    else:
        bot.send_document(message.chat.id, open(outputcsvname, 'rb'))


@bot.message_handler(commands=['forceadd'])
def forceadd(message):
    if(message.chat.username == admin_user_name):
        msg = bot.reply_to(
            message, "Please enter the [name,number] of the student you want to add")
        bot.register_next_step_handler(msg, forceaddstep)
    else:
        bot.send_message(
            message.chat.id, "You are not allowed to use this command.")


@bot.message_handler(commands=['swap'])
def forceadd(message):
    if(message.chat.username == admin_user_name):
        msg = bot.reply_to(
            message, "Please enter the [num1,num2] of the student you want to add")
        bot.register_next_step_handler(msg, swapstep)
    else:
        bot.send_message(
            message.chat.id, "You are not allowed to use this command.")


@bot.message_handler(commands=['restorecsv'])
def restorecsv(message):
    if(message.chat.username == admin_user_name):
        bot.reply_to(message, "Please send the csv file to restore")
        bot.register_next_step_handler(message, restorecsvstep)
    else:
        bot.send_message(
            message.chat.id, "You are not allowed to use this command.")


@bot.message_handler(commands=['backup'])
def backup(message):
    f = open(outputcsvname, 'rb')
    sha = repository.get_contents(outputcsvname).sha
    repository.update_file(
        outputcsvname, "create_file via PyGithub", f.read(), sha)
    bot.reply_to(message, "`    Backup done `")


while True:
    try:
        bot.polling(none_stop=True)

    except Exception as e:
        print(e)
        time.sleep(15)
