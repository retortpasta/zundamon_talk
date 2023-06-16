import json
import asyncio
import configparser
from time import time
from random import randint
from collections import deque
from typing import Dict, List, Any, Tuple

import openai
import requests
import PySimpleGUI as gui
from playsound import playsound


def main() -> None:
    gui.theme(gui.theme_list()[randint(0, len(gui.theme_list()) - 1)])
    window = gui.Window(title="Immediately Zundamon", layout=gui_layout(), finalize=True)

    openai.api_key = api_key()
    speaker_id: int = speaker()[window["speaker_name"].get()][window["speaker_style"].get()]

    while True:
        event, value = window.read()

        if event is None:
            break

        if event == "password":
            window["token"].update(password_char=["*", ""][window[event].get()])

        if event == "speaker_name":
            styles = tuple(key for key in speaker()[window["speaker_name"].get()])
            window["speaker_style"].update(values=styles)
            window["speaker_style"].update(value=styles[0])

        if event in ["speaker_style", "speaker_name"]:
            speaker_id = speaker()[window["speaker_name"].get()][window["speaker_style"].get()]

        if event == "gpt":
            asyncio.new_event_loop().run_in_executor(None, parse, window["text"].get(), speaker_id)

    window.close()


def gui_layout() -> List[List[Any]]:
    return [
        [gui.Text(text="API Key: "),
         gui.InputText(default_text=api_key(), key="token", disabled=True, password_char="*"),
         gui.Check(text="表示", key="password", enable_events=True, default=False)],
        [gui.Text(text="話者: "),
         gui.DropDown(values=(name := tuple([key for key in speaker().keys()])),
                      default_value=name[0],
                      size=(20, 1),
                      enable_events=True,
                      key="speaker_name"),
         gui.Text(text="話法: "),
         gui.DropDown(values=(style := tuple([key for key in speaker()[name[0]].keys()])),
                      default_value=style[0],
                      size=(20, 1),
                      enable_events=True,
                      key="speaker_style")],
        [gui.Input(key="text"), gui.Button(button_text="GPT", key="gpt")]

    ]


def parse(request_string, speaker_id):
    response_string: str = ""
    for response in chat_gpt_call(request_string):
        response = response.replace("\n", "")
        if response == "":
            continue
        split_response, f = split(response_string + response, "、。？！")
        if not f:
            response_string = split_response.pop()
        else:
            response_string = ""
        for i in split_response:
            print(f"テキスト: {i}")
            start = time()
            voicevox_call(i, speaker_id)
            print(f"生成時間: {time() - start}")


def chat_gpt_call(text):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": text}
        ],
        temperature=0,
        stream=True
    )

    for chunk in response:
        chunk_message = chunk["choices"][0]["delta"]
        yield chunk_message.get("content", "")


def voicevox_call(text: str, speaker_id: int):
    response = requests.post("http://localhost:50021/audio_query", params={"text": text, "speaker": speaker_id})
    audio = requests.post("http://localhost:50021/synthesis",
                          params={"speaker": speaker_id}, data=json.dumps(response.json()))
    with open(file=f"./test/{text}.wav", mode="wb") as file:
        file.write(audio.content)
    playsound(f"./test/{text}.wav")


def split(text: str, delimiter: str) -> Tuple[deque, bool]:
    def _split(_text: str, _char: str) -> deque:
        if any(char in _text for char in _char):
            index = min([_text.find(char) for char in _char if char in _text])
            front = _text[:index + 1]
            back = _text[index + 1:]
            q = _split(back, _char)
            q.appendleft(front)
            return q
        else:
            if _text == "":
                return deque()
            return deque([_text])

    if text == "":
        return deque(), False
    split_text = _split(text, delimiter)
    return split_text, any(char in split_text[-1] for char in delimiter)


def api_key() -> str:
    cfg = configparser.ConfigParser()
    cfg.read(filenames="./resources/OpenAI.ini", encoding="UTF-8")
    return cfg["OpenAI"].get("api_key")


def speaker() -> Dict[str, Dict[str, int]]:
    cfg = configparser.ConfigParser()
    cfg.read(filenames="./resources/Voice.ini", encoding="UTF-8")
    speakers = dict()
    for section in cfg.sections():
        speakers[section] = {style: int(cfg[section].get(style)) for style in cfg[section]}
    return speakers


if __name__ == "__main__":
    main()
