import streamlit as st
from docx import Document
from supabase import create_client
import random
import string
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Quiz Técnico WLI", layout="wide")

# --- 2. CONEXÃO COM O SUPABASE ---
# Certifique-se de que os nomes no secrets.toml estão exatamente assim
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Atualiza a tela automaticamente para sincronizar admin e jogadores
st_autorefresh(interval=2000, key="frequencia_quiz")

# --- 3. FUNÇÃO PARA LER O WORD (DIVIDIDA PARA EVITAR ERROS) ---
def parse_word_file(file):
    doc = Document(file)
    full_text = []
    
    # Extrai o texto de cada parágrafo ignorando linhas vazias
    for p in doc.paragraphs:
        texto_limpo = p.text.strip()
        if texto_limpo:
            full_text.append(texto_limpo)
    
    qa_pairs = []
    # Organiza em pares: parágrafo i (questão) e i+1 (resposta)
    for i in range(0, len(full_text), 2):
        if i + 1 < len(full_text):
            par = {
                "question_text_quiz": full_text[i],
                "answer_text_quiz": full_text[i+1]
            }
            qa_pairs.append(par)
    return qa_pairs

# --- 4. ESTILO CSS (VISUAL DO EXCEL) ---
st.markdown("""
    <style>
    .pergunta-box {
        background-color: #DDEBF7;
        padding: 30px;
        border: 2px solid #000;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        border-radius: 8px;
    }
    .timer-display {
        background-color: #7F7F7F;
        color: white;
        padding: 15px;
        font-size: 45px;
        text-align: center;
        font-weight: bold;
        width: 150px;
        margin: 20px auto;
    }
    .mao-alerta {
        background-color: red;
        color: white;
        padding: 20px;
        text-align: center;
        font-size: 35px;
        font-weight: bold;
        border: 4px solid #000;
        border-radius: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. SISTEMA DE LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = {'logged': False, 'role': None}

if not st.session_state.auth['logged']:
    st.title("Acesso ao Quiz")
    user_name = st.text_input("Seu Nome/Apelido")
    user_pass = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        # Verifica se é Admin
        if user_pass == st.secrets["ADMIN_PASSWORD"]:
            # Gera nova senha mestre dinamicamente
            nova_senha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            supabase.table("game_state_quiz").update({"master_password_quiz": nova_senha}).eq("id_quiz", 1).execute()
            
            st.session_state.auth = {'logged': True, 'role': 'admin'}
            st.rerun()
        else:
            # Verifica senha para Jogador
            res = supabase.table("game_state_quiz").select("master_password_quiz").eq("id_quiz", 1).single().execute()
            if user_pass == res.data['master_password_quiz']:
                st.session_state.auth = {'logged': True, 'role': 'player'}
                supabase.table("players_quiz").insert({"nickname_quiz": user_name}).execute()
                st.rerun()
            else:
                st.error("Senha inválida ou o Admin ainda não iniciou a sessão.")

# --- 6. PAINEL DO ADMINISTRADOR ---
elif st.session_state.auth['role'] == 'admin':
    st.sidebar.title("🛠️ Painel Admin")
    estado = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    
    st.sidebar.info(f"SENHA PARA JOGADORES: {estado['master_password_quiz']}")
    
    # Upload e Processamento
    doc_file = st.sidebar.file_uploader("Arquivo Word das Questões", type="docx")
    if doc_file and st.sidebar.button("Carregar Questões"):
        dados_questoes = parse_word_file(doc_file)
        supabase.table("questions_quiz").delete().neq("id_quiz", 0).execute()
        supabase.table("questions_quiz").insert(dados_questoes).execute()
        st.sidebar.success("Questões enviadas com sucesso!")

    # Controles do Quiz
    tempo = st.sidebar.number_input("Segundos", value=15)
    idx = st.sidebar.number_input("Questão Atual (Índice)", value=0)
    
    if st.sidebar.button("🚀 INICIAR CRONÔMETRO"):
        supabase.table("game_state_quiz").update({
            "is_active_quiz": True,
            "timer_duration_quiz": tempo,
            "current_question_index_quiz": idx,
            "show_answer_quiz": False,
            "start_time_quiz": int(time.time())
        }).eq("id_quiz", 1).execute()

    if st.sidebar.button("✅ MOSTRAR RESPOSTA"):
        supabase.table("game_state_quiz").update({"show_answer_quiz": True, "is_active_quiz": False}).eq("id_quiz", 1).execute()

# --- 7. TELA DO JOGO (SINCRONIZADA) ---
if st.session_state.auth['logged']:
    st.markdown('<h2 style="text-align:center;">TESTE DE CONHECIMENTO - FABRICAÇÃO WLI</h2>', unsafe_allow_html=True)
    
    estado = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    perguntas = supabase.table("questions_quiz").select("*").order("id_quiz").execute().data
    
    if perguntas and estado['current_question_index_quiz'] < len(perguntas):
        p_atual = perguntas[estado['current_question_index_quiz']]
        
        # Caixa da Questão
        st.markdown(f'<div class="pergunta-box">{p_atual["question_text_quiz"]}</div>', unsafe_allow_html=True)
        
        # Lógica do Timer
        if estado['is_active_quiz']:
            agora = int(time.time())
            decorrido = agora - estado['start_time_quiz']
            restante = max(0, estado['timer_duration_quiz'] - decorrido)
            
            st.markdown(f'<div class="timer-display">{restante}</div>', unsafe_allow_html=True)
            
            if restante == 0:
                st.markdown('<div class="mao-alerta">✋ LEVANTE A MÃO E RESPONDA!</div>', unsafe_allow_html=True)
        
        # Resposta
        if estado['show_answer_quiz']:
            st.success(f"**RESPOSTA:** {p_atual['answer_text_quiz']}")
    else:
        st.info("Aguardando o Administrador carregar perguntas ou iniciar o jogo.")
