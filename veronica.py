import os
import sqlite3
import threading
import time
import speech_recognition as sr
import pyttsx3

# Função para inicializar o banco de dados e garantir que as tabelas existam
def init_db():
    conn = sqlite3.connect('veronica.db')
    cursor = conn.cursor()
    
    # Criando tabela de intenções, caso não exista
    cursor.execute('''CREATE TABLE IF NOT EXISTS intents (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT)''')
    
    # Criando tabela de respostas, caso não exista
    cursor.execute('''CREATE TABLE IF NOT EXISTS responses (
                        id INTEGER PRIMARY KEY,
                        intent_id INTEGER,
                        response_text TEXT NOT NULL,
                        FOREIGN KEY (intent_id) REFERENCES intents(id))''')
    
    # Criando tabela de interações para registrar falhas de entendimento
    cursor.execute('''CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY,
                        command TEXT,
                        response TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    # Tabela para registrar feedback de aprendizado (comando não entendido)
    cursor.execute('''CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY,
                        command TEXT,
                        feedback TEXT)''')
    
    conn.commit()
    conn.close()

# Função para registrar interações no banco de dados
def log_interaction(command, response):
    conn = sqlite3.connect('veronica.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO interactions (command, response) VALUES (?, ?)', (command, response))
    conn.commit()
    conn.close()

# Função para registrar feedback
def log_feedback(command, feedback):
    conn = sqlite3.connect('veronica.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO feedback (command, feedback) VALUES (?, ?)', (command, feedback))
    conn.commit()
    conn.close()

# Função de síntese de voz (resposta por voz)
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Ajustando a velocidade da fala

def speak(text):
    engine.say(text)
    engine.runAndWait()

# Função para ouvir o comando do usuário
def listen(prompt="Aguardando comando...", timeout=None, phrase_time_limit=None):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print(prompt)
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            print("Nenhum áudio detectado dentro do tempo limite.")
            return ""

    try:
        command = recognizer.recognize_google(audio, language='pt-BR')
        print(f"Você disse: {command}")
        return command.lower()
      except sr.UnknownValueError:  
        print("Não consegui entender, por favor, tente novamente.")
        return ""
    except sr.RequestError:
        print("Erro ao tentar se conectar ao serviço de reconhecimento de voz.")
        return ""

# Função para processar os comandos de voz
def process_command(command):␊
    if "verônica" in command or "vê" in command:  # Incluindo variações como "Vê"␊
        command = command.replace("verônica", "").replace("vê", "").strip()  # Remove a palavra-chave␊
␊
        # Consultar o banco de dados para encontrar uma intenção correspondente␊
        response = check_intent(command)␊

        if response:␊
            # Log da interação␊
            log_interaction(command, response)␊
            # Falar a resposta␊
            speak(response)␊
        else:␊
            # Se a Verônica não entender, ela pedirá feedback␊
            speak("Desculpe, não entendi o comando. Você pode me explicar o que deseja fazer?")␊
            threading.Thread(target=save_feedback, args=(command,), daemon=True).start()
            return  # Volta para o loop de escuta␊

# Função para verificar a intenção no banco de dados e retornar a resposta
def check_intent(command):
    conn = sqlite3.connect('veronica.db')
    cursor = conn.cursor()
    
    # Busca por intenções que correspondem ao comando
    cursor.execute("SELECT r.response_text FROM intents i "
                   "JOIN responses r ON i.id = r.intent_id "
                   "WHERE ? LIKE '%' || i.name || '%'", (command,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]  # Retorna a resposta correspondente
    else:
        return None

# Função para salvar o feedback de quando a Verônica não entender o comando
def save_feedback(command):
    feedback_prompt = f"Você pode me explicar o comando '{command}'?"
    feedback = listen(prompt=feedback_prompt, timeout=5, phrase_time_limit=10)
    if not feedback:
        feedback = "feedback não fornecido"
    log_feedback(command, feedback)

# Função para rodar o assistente em segundo plano
def run_assistant():
    while True:
        command = listen()
        if command:
            process_command(command)
        time.sleep(1)  # Adiciona um pequeno atraso para não sobrecarregar o processador

# Função principal que inicia a Verônica
def start_assistant():
    init_db()  # Inicializa o banco de dados
    assistant_thread = threading.Thread(target=run_assistant, daemon=True)
    assistant_thread.start()
    print("Assistente Verônica está rodando em segundo plano.")
    while True:
        time.sleep(1)  # Mantém o assistente rodando em segundo plano sem consumir muitos recursos

if __name__ == "__main__":
    start_assistant()

