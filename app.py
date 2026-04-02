import streamlit as st
from docx import Document
from supabase import create_client
import random
import string
import time

from streamlit_autorefresh import st_autorefresh

# Atualiza o app a cada 2 segundos para sincronizar com o banco de dados
st_autorefresh(interval=2000, key="quiz_sync")


# --- CONEXÃO ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- FUNÇÕES DE APOIO ---
def parse_word_file(file):
    doc = Document(file)
    full_text =
    
    # Lógica: Linha 1 Pergunta, Linha 2 Resposta, pula-se uma linha (já ignorada pelo if acima)
    qa_pairs = []
    for i in range(0, len(full_text), 2):
        if i + 1 < len(full_text):
            qa_pairs.append({
                "question_text_quiz": full_text[i],
                "answer_text_quiz": full_text[i+1]
            })
    return qa_pairs

def update_db_questions(data):
    # Limpa perguntas antigas e insere novas
    supabase.table("questions_quiz").delete().neq("id_quiz", 0).execute()
    supabase.table("questions_quiz").insert(data).execute()

# --- CSS PERSONALIZADO (Estilo da Imagem) ---
st.markdown("""
    <style>
    .question-container {
        background-color: #DDEBF7;
        padding: 30px;
        border: 2px solid #000;
        text-align: center;
        font-size: 22px;
        min-height: 150px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .timer-box {
        background-color: #4472C4;
        color: white;
        padding: 15px;
        font-size: 40px;
        text-align: center;
        font-weight: bold;
    }
    .hand-signal {
        background-color: #FF0000;
        color: white;
        padding: 20px;
        font-size: 35px;
        font-weight: bold;
        text-align: center;
        border-radius: 10px;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if 'auth_state' not in st.session_state:
    st.session_state.auth_state = {'logged': False, 'role': None, 'user': ""}

if not st.session_state.auth_state['logged']:
    st.title("Início - Quiz Técnico")
    user = st.text_input("Nome/Apelido")
    pwd = st.text_input("Senha de Acesso", type="password")
    
    if st.button("Entrar"):
        if pwd == st.secrets["ADMIN_PASSWORD"]:
            st.session_state.auth_state = {'logged': True, 'role': 'admin', 'user': user}
            # Gera nova senha mestre ao admin entrar
            new_master = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            supabase.table("game_state_quiz").update({"master_password_quiz": new_master}).eq("id_quiz", 1).execute()
            st.rerun()
        else:
            # Verifica senha mestre no banco
            res = supabase.table("game_state_quiz").select("master_password_quiz").eq("id_quiz", 1).single().execute()
            if pwd == res.data['master_password_quiz']:
                st.session_state.auth_state = {'logged': True, 'role': 'player', 'user': user}
                supabase.table("players_quiz").insert({"nickname_quiz": user}).execute()
                st.rerun()
            else:
                st.error("Senha inválida.")

# --- ÁREA DO ADMINISTRADOR ---
elif st.session_state.auth_state['role'] == 'admin':
    st.sidebar.header("Painel de Controle")
    state = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    
    st.sidebar.warning(f"SENHA ATUAL: {state['master_password_quiz']}")
    
    # Upload do Word
    uploaded_file = st.sidebar.file_uploader("Upload Perguntas (Word)", type="docx")
    if uploaded_file and st.sidebar.button("Processar Arquivo"):
        qa_data = parse_word_file(uploaded_file)
        update_db_questions(qa_data)
        st.sidebar.success(f"{len(qa_data)} perguntas carregadas!")

    # Controle do Jogo
    t_input = st.sidebar.number_input("Tempo (seg)", value=15)
    q_index = st.sidebar.number_input("Índice da Pergunta", value=0)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ INICIAR TIMER"):
            supabase.table("game_state_quiz").update({
                "is_active_quiz": True, 
                "timer_duration_quiz": t_input,
                "current_question_index_quiz": q_index,
                "show_answer_quiz": False
            }).eq("id_quiz", 1).execute()
    with col2:
        if st.button("🔓 MOSTRAR RESPOSTA"):
            supabase.table("game_state_quiz").update({"show_answer_quiz": True, "is_active_quiz": False}).eq("id_quiz", 1).execute()

    # Lista de Jogadores
    st.sidebar.divider()
    st.sidebar.subheader("Jogadores")
    players = supabase.table("players_quiz").select("*").execute().data
    for p in players:
        if st.sidebar.button(f"Excluir {p['nickname_quiz']}"):
            supabase.table("players_quiz").delete().eq("id_quiz", p['id_quiz']).execute()
            st.rerun()

# --- TELA DE EXIBIÇÃO (Admin e Player) ---
if st.session_state.auth_state['logged']:
    # Auto-refresh simples para sincronizar jogadores (ex: a cada 2 seg)
    # Recomenda-se: from streamlit_autorefresh import st_autorefresh
    # st_autorefresh(interval=2000, key="datarefresh")

    state = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    questions = supabase.table("questions_quiz").select("*").order("id_quiz").execute().data
    
    if questions and state['current_question_index_quiz'] < len(questions):
        q = questions[state['current_question_index_quiz']]
        
        st.markdown(f'<div class="question-container">{q["question_text_quiz"]}</div>', unsafe_allow_html=True)
        
        if state['is_active_quiz']:
            # Simulação de contador (no Streamlit o ideal é usar st_autorefresh)
            st.markdown(f'<div class="timer-box">TEMPO: {state["timer_duration_quiz"]}s</div>', unsafe_allow_html=True)
            # Ao final do tempo (lógica manual ou por JS), mostra-se a mão
            st.markdown('<div class="hand-signal">✋ LEVANTE A MÃO E RESPONDA!</div>', unsafe_allow_html=True)

        if state['show_answer_quiz']:
            st.success(f"RESPOSTA: {q['answer_text_quiz']}")
    else:
        st.info("Aguardando o administrador carregar as perguntas ou iniciar o jogo.")
