import argparse
import os
import sys
from pathlib import Path
import random

import requests
from dotenv import load_dotenv


def get_max_comics_number():
    url = 'https://xkcd.com/info.0.json'
    response = requests.get(url)
    response.raise_for_status()
    max_comics_number = response.json()['num']
    return max_comics_number


def get_comics(comics_number: int):
    url = f'https://xkcd.com/{comics_number}/info.0.json'
    response = requests.get(url)
    response.raise_for_status()
    comics = response.json()
    return comics


def get_implicit_token(client_id: int, v: float):
    url = f'https://oauth.vk.com/authorize?client_id={client_id}' \
          f'&display=page&scope=photos,groups,wall,offline' \
          f'&response_type=token&v={v}'
    response = requests.get(url)
    response.raise_for_status()
    return response.url


def check_vk_status(vk_response):
    if 'error' in vk_response:
        raise requests.HTTPError(vk_response['error'])


def get_upload_url(token: str, group_id: int, v: float, method_name: str):
    params = {
        'group_id': group_id,
        'access_token': token,
        'v': v
    }
    url = f'https://api.vk.com/method/{method_name}'
    response = requests.get(url, params=params)
    response.raise_for_status()
    vk_response = response.json()
    check_vk_status(vk_response=vk_response)
    return vk_response['response']['upload_url']


def send_image(url: str, image: str):
    with open(image, 'rb') as file:
        files = {
            'file': file,
        }
        response = requests.post(url, files=files)
        response.raise_for_status()
        vk_response = response.json()
        check_vk_status(vk_response=vk_response)
        return vk_response


def save_image_to_group(token: str, group_id: int,
                        method_name: str, photo_hash: str,
                        photo: list, server: int, v: float):
    params = {
        'group_id': group_id,
        'photo': photo,
        'hash': photo_hash,
        'server': server,
        'access_token': token,
        'v': v
    }
    url = f'https://api.vk.com/method/{method_name}'
    response = requests.post(url, params=params)
    response.raise_for_status()
    vk_response = response.json()
    check_vk_status(vk_response=vk_response)
    return vk_response


def post_image_to_group(token: str, group_id: int,
                        v: float, method_name: str,
                        photo_id: int, owner_id: int,
                        message: str):
    params = {
        'group_id': group_id,
        'owner_id': f'-{group_id}',
        'access_token': token,
        'from_group': 1,
        'attachments': f'photo{owner_id}_{photo_id}',
        'message': message,
        'v': v
    }
    url = f'https://api.vk.com/method/{method_name}'
    response = requests.post(url, params=params)
    check_vk_status(vk_response=response.json())
    response.raise_for_status()


def save_image_local(url: str, folder: str, filename: str):
    response = requests.get(url)
    response.raise_for_status()
    with open(f'{folder}/{filename}.png', 'wb') as image:
        image.write(response.content)
        return f'{folder}/{filename}.png'


def main():
    load_dotenv()
    comics_number = random.randint(1, get_max_comics_number())
    v = float(os.getenv('V'))
    client_id = int(os.getenv('CLIENT_ID'))
    access_token = os.getenv('ACCESS_TOKEN')
    group_id = int(os.getenv('GROUP_ID'))
    img_folder = os.getenv('IMAGE_FOLDER')
    Path(img_folder).mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser(description='Posting comics to VK-group')
    parser.add_argument('--token', choices=['get'],
                        help='Getting VK access token ')
    args = parser.parse_args()
    if args.token == 'token':
        try:
            print(get_implicit_token(client_id=int(client_id), v=float(v)))
            print('?????????????????? ???? ???????????? ????????, ?????????????????? ???????????? ????????????????????,'
                  '?? ???????????? ACCESS_TOKEN ?????????? ?? ?????????????????? "&access_token=".'
                  ' ?????????????? ?????? ?? .env ?? ?????????????????????????? ???????????? ?????? ????????????????????')
            sys.exit()
        except requests.exceptions.HTTPError as e:
            print(e)
            print('??????????????????, ???????????? ???? ID ?? ???????????????????? ???????????? V ?? env')
    try:
        comics = get_comics(comics_number=comics_number)
        comics_text = comics['alt']
        comics_image_path = save_image_local(
            url=comics['img'],
            folder=img_folder,
            filename=comics['safe_title']
        )
    except requests.exceptions.HTTPError as e:
        print(e)
        print('???????????? ???? ????????????')
    try:
        upload_url = get_upload_url(
            token=access_token,
            group_id=group_id,
            v=v,
            method_name='photos.getWallUploadServer'
        )
        photo_upload_params = send_image(
            url=upload_url,
            image=comics_image_path
        )
        photo_uploaded = save_image_to_group(
            token=access_token,
            group_id=group_id,
            v=v,
            method_name='photos.saveWallPhoto',
            photo_hash=photo_upload_params['hash'],
            server=photo_upload_params['server'],
            photo=photo_upload_params['photo']
        )
        post_image_to_group(
            token=access_token,
            group_id=group_id,
            v=v,method_name='wall.post',
            photo_id=photo_uploaded['response'][0]['id'],
            owner_id=photo_uploaded['response'][0]['owner_id'],
            message=comics_text
        )
    except requests.exceptions.HTTPError as e:
        print(e)
    finally:
        os.remove(comics_image_path)


if __name__ == '__main__':
    main()
