from vk_api.utils import get_random_id
import pickle

with open('messages.pickle', 'rb') as file:
	messages_dict = pickle.load(file)

def print_settings(config, peer_id, vk_obj):
	text = messages_dict['settings_text']
	user_settings = f'''\n\n ✅Ваши текущие настройки:\n base: {config["base"]} \n interval: {config["interval"]}'''
	vk_obj.messages.send(peer_id=peer_id, random_id=get_random_id(), message=text+user_settings)

def print_greeeting(peer_id, vk_obj):
	vk_obj.messages.send(peer_id=peer_id, random_id=get_random_id(), message=messages_dict['greeting_text'])

def print_size(size, peer_id, vk_obj):
	text = f'Текущий размер базы: {size}'
	vk_obj.messages.send(peer_id=peer_id, random_id=get_random_id(), message=text)
