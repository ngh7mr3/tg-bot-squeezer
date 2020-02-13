#!/usr/bin/env python3
import time
import os
import telebot
from constants import *
import logging
from concurrent.futures import ThreadPoolExecutor
import flask
import requests
from collections import deque

BOT = telebot.TeleBot(API_TOKEN)

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

SERVER = flask.Flask(__name__)
EXECUTOR = ThreadPoolExecutor(5)

QUEUE = 1

@SERVER.route('/', methods=['GET', 'POST'])
def index():
	return ''

@SERVER.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
	if flask.request.headers.get('content-type') == 'application/json':
		json_string = flask.request.get_data().decode('utf-8')
		update = telebot.types.Update.de_json(json_string)
		BOT.process_new_updates([update])
		return ''
	else:
		flask.abort(403)

@BOT.message_handler(commands = ['start'])
def handle_start_message(message):
	#database - new user
	#DB.new_user(message.chat.id)
	SERVER.logger.info("\nNew registered user: %s, chat_id - %d" % ('test', message.chat.id))
	
	BOT.send_message(message.chat.id, "Oh, hi there!")

@BOT.message_handler(content_types = ['text'])
def handle_text_message(message):
	SERVER.logger.info("\nUser: %s\nMessage: %s" % (str(message.chat.id), message.text))
	if message.chat.id != ADMIN_CHAT_ID:
		msg = "User %s, %d: %s"%(message.chat.username, message.chat.id, message.text)
		BOT.send_message(ADMIN_CHAT_ID, msg)
	BOT.send_message(message.chat.id, "Cool!\nNow send your photo")

@BOT.message_handler(content_types = ['photo'])
def handle_photo(message):
	global QUEUE

	SERVER.logger.info("\nGot photo from user: %s (@%s)" % (message.chat.id, message.chat.username))
	BOT.reply_to(message, "Great!\nWait till I'll squeeze it, your position in queue: %d"%QUEUE)
	for _,i in enumerate(message.photo):
		SERVER.logger.debug("message.photo[%d]: %s" % (_, str(i)))
	EXECUTOR.submit(process_photo, message.chat.id, message.photo.pop().file_id)

	QUEUE+=1

#BOT.remove_webhook()
#time.sleep(2)
#BOT.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH,
#				certificate=open(WEBHOOK_SSL_CERT, 'r'))

def process_photo(chat_id, file_id):
	global QUEUE

	SERVER.logger.info("Started processing photo {0}".format(file_id))
	
	# store file in temp folder
	file_info = BOT.get_file(file_id)
	file = requests.get(TELEGRAM_PREFIX.format(API_TOKEN, file_info.file_path))

	SERVER.logger.debug("Length of file.content: %d" % len(file.content))

	open('temp/{0}'.format(file_id+'.jpg'), 'wb').write(file.content)
	SERVER.logger.debug("Successfully downloaded file: "+str(os.path.exists('temp/{0}'.format(file_id+'.jpg'))))

	# process file with image magick
	os.system(IM_CMD.format('temp/'+file_id+'.jpg'))
	SERVER.logger.info("Ended processing photo {0}".format(file_id))

	# send file to user
	file_handle = open('temp/{0}'.format(file_id+'.jpg'), 'rb')
	BOT.send_photo(chat_id, file_handle)
	file_handle.close()

	# delete photo from temp folder
	os.system('rm temp/{0}.jpg'.format(file_id))

	QUEUE-=1

if __name__ == "__main__":
	SERVER.logger.setLevel(logging.DEBUG)
	FH = logging.FileHandler('bot.log')
	FH.setLevel(logging.DEBUG)
	SERVER.logger.addHandler(FH)
	SERVER.run(host=WEBHOOK_LISTEN,
			port=WEBHOOK_PORT,
			ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV),
			debug=True)
