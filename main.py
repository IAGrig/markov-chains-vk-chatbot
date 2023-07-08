import pickle
import random
import os
from dotenv import load_dotenv
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from loguru import logger
from messages import print_greeeting, print_settings, print_size

DIRNAME = os.path.dirname(os.path.abspath(__file__)) + os.sep


def get_tokens(text):
	words = text.lower().split()
	if words[0] == '*START*':
		del words[0]
	elif words[-1] == '*END*':
		del words[-1]
	return words


def train(base, tokens):
	tokens = ['*START*'] + tokens + ['*END*']
	for i in range(len(tokens)):
		if tokens[i] == '*start*':
			tokens[i] = '*START*'
		elif tokens[i] == '*end*':
			tokens[i] = '*END*'
		else:
			continue
	for i in range(len(tokens) - 1):
		if tokens[i] in base:
			if tokens[i + 1] in base[tokens[i]]:
				base[tokens[i]][tokens[i + 1]] += 1
			else:
				base[tokens[i]][tokens[i + 1]] = 1
		else:
			base[tokens[i]] = {tokens[i + 1]: 1}
	return base


def get_random_word(word, base):
	lst = []
	for i in base[word].items():
		for n in range(i[1]):
			lst.append(i[0])
	return random.choice(lst)


def generate(base):
	if len(base):
		answer = ['*START*']
		i = 0
		while answer[i] != '*END*':
			answer.append(get_random_word(answer[i], base))
			i += 1
		return ' '.join(answer[1:-1])
	return "Извините, база пуста(("


def send_message(vk_obj, peer_id, text):
	vk_obj.messages.send(peer_id=peer_id, random_id=get_random_id(), message=text)


def send_new_phrase(vk_obj, peer_id, base):
	vk_obj.messages.send(peer_id=peer_id, random_id=get_random_id(),
	                     message=generate(base))


def get_config(peer_id):
	if os.path.exists(DIRNAME + os.sep + "configs.pickle"):
		with open('configs.pickle', 'rb') as file:
			configs = pickle.load(file)
	else:
		configs = {}
	if peer_id not in configs:
		configs[peer_id] = {'base': 'self',
		                    'interval': 12,
		                    'messages_count': 0}
	return configs[peer_id]


def set_config(peer_id, key, value):
	if os.path.exists(DIRNAME + os.sep + "configs.pickle"):
		with open('configs.pickle', 'rb') as file:
			configs = pickle.load(file)
	else:
		configs = {}
	if peer_id not in configs:
		configs[peer_id] = {'base': 'self',
		                    'interval': 12,
		                    'messages_count': 0}
	configs[peer_id][key] = value
	with open('configs.pickle', 'wb') as file:
		pickle.dump(configs, file)


def main():
	if not os.path.exists(DIRNAME):
		os.mkdir(DIRNAME)
	logger.add(f"{DIRNAME}logs{os.sep}logs.txt", format='{time} {level} {message}', level="DEBUG", rotation="1 week",
	           compression="zip")
	logger.info('Запуск бота...')
	load_dotenv()
	token = os.getenv('TOKEN')
	group_id = int(os.getenv('GROUP_ID'))
	logger.info('Переменные окружения загружены')
	vk_session = vk_api.VkApi(token=token)
	vk = vk_session.get_api()
	logger.info('Доступ к vk_api получен. Запускаем longpoll')
	longpoll = VkBotLongPoll(vk_session, group_id)
	try:
		for event in longpoll.listen():
			if event.type == VkBotEventType.MESSAGE_NEW:
				message = event.object['message']
				config = get_config(message['peer_id'])
				try:
					if config['base'] == 'self':
						with open(f"{DIRNAME}bases{os.sep}peer{message['peer_id']}base.pickle", 'rb') as file:
							base = pickle.load(file)
					elif config['base'] == 'global':
						with open(f"{DIRNAME}bases{os.sep}global.pickle", 'rb') as file:
							base = pickle.load(file)
					else:
						logger.error(f'unknown base config: {config["base"]}')
				except Exception as e:
					logger.error(e)
					base = {}

				# message handling
				if message['text'].lower().startswith('dg'):
					if message['text'] == 'dg help':
						print_greeeting(message['peer_id'], vk)
					elif message['text'] == 'dg settings':
						print_settings(config, message['peer_id'], vk)
					elif message['text'] in ('dg s', 'dg speak'):
						send_new_phrase(vk, message['peer_id'], base)
					elif message['text'] == 'dg i':
						size = 0
						for key in base:
							size += len(base[key])
						print_size(size, message['peer_id'], vk)

					elif message['text'] == 'DG ReSeT': # !check admin status in future
						if config['base'] == 'self':
							base = {}
							with open(f"bases{os.sep}peer{message['peer_id']}base.pickle", 'wb') as file:
								pickle.dump(base, file)
							send_message(vk, message['peer_id'], '❗✅База полностью сброшена')
						elif config['base'] == 'global':
							send_message(vk, message['peer_id'], 'Вы не можете сбросить общую базу')
						else:
							logger.error(f'unknown base config: {config["base"]}')

					elif message['text'].startswith('dg set'):
						commands = message['text'].lower().split()
						if commands[2] == 'base':
							if commands[3] in ('global', 'self'):
								key, value = commands[2], commands[3]
								set_config(message['peer_id'], key, value)
								send_message(vk, message['peer_id'], f'Значение для базы установлено в {value}')
							else:
								send_message(vk, message['peer_id'], 'Неверный параметр при настройке базы')
						elif commands[2] == 'interval':
							try:
								interval = int(commands[3])
							except:
								send_message(vk, message['peer_id'], 'Указано не число при настройке интервала')
							else:
								if 3 <= interval <= 10000:
									set_config(message['peer_id'], 'interval', interval)
									send_message(vk, message['peer_id'], f'Интервал теперь {interval} сообщений')
								else:
									send_message(vk, message['peer_id'], 'Значение интервала не входит в допустимый диапазон')
						else:
							send_message(vk, message['peer_id'], 'Нераспознанный параметр настройки')
				# usual messages
				else:
					try:
						if message['from_id'] > 0:
							interval = config['interval']
							messages_count = config['messages_count'] + 1
							user = vk.users.get(user_ids=message['from_id'])[0]
							tokens = get_tokens(message['text'])
							base = train(base, tokens)
							print(
								f"{user['first_name']} {user['last_name']} написал: {message['text']}")  # it's just debugging
							if messages_count >= interval:
								send_new_phrase(vk, message['peer_id'], base)
								messages_count = 0
					except Exception as e:
						logger.error(e)
					finally:
						set_config(message['peer_id'], 'messages_count', messages_count)
						if config['base'] == 'self':
							with open(f"bases{os.sep}peer{message['peer_id']}base.pickle", 'wb') as file:
								pickle.dump(base, file)
						elif config['base'] == 'global':
							with open(f'bases{os.sep}global.pickle') as file:
								pickle.dump(base, file)
						else:
							logger.error(f'unknown base config: {config["base"]}')

			elif event.type == VkBotEventType.GROUP_JOIN:
				if event.object['user_id'] == -191755513:
					peer = message['peer_id']
					print_greeeting(peer, vk)

	except Exception as e:
		logger.error(e)
		logger.info('Перезапуск бота...')
		main()


if __name__ == '__main__':
	main()

# Here is an example of message event
'''<<class 'vk_api.bot_longpoll.VkBotMessageEvent'>({'type': 'message_new', 'object': {'message': {'date': 
1635700126, 'from_id': <user_id>, 'id': 186, 'out': 0, 'peer_id': 430579732, 'text': 'hi', 'conversation_message_id': 
187, 'fwd_messages': [], 'important': False, 'random_id': 0, 'attachments': [], 'is_hidden': False}, 'client_info': {
'button_actions': ['text', 'vkpay', 'open_app', 'location', 'open_link', 'callback', 'intent_subscribe', 
'intent_unsubscribe'], 'keyboard': True, 'inline_keyboard': True, 'carousel': True, 'lang_id': 0}}, 'group_id': 
191755513, 'event_id': '962a5a5320992a015701c8fd2e4bf20f462da293'})> '''
