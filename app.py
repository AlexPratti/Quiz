import streamlit as st
from docx import Document
from supabase import create_client
import random
import string
import time
from streamlit_autorefresh import st_autorefresh

# 1. Configurações Iniciais e Conexão
st.set_page_config(page_title="Quiz WLI", layout="wide")
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Atualiza o app a cada 2 segundos para sincronizar Admin e Jogadores
st_autorefresh(interval=2000, key="quiz_sync")

# 2. Funções de Suporte
def parse_word_file(file):
    doc = Document(file)
    # Pega apenas os parágrafos que têm texto (ignora linhas vazias entre perguntas)
    full_text =
    
    qa_pairs = []
    # Pula de 2 em 2: Linha 1=Pergunta, Linha 2=Resposta
    for i in range(0, len(full_text), 2):
        if i + 1 < len(full_text):
            qa_pairs.append({
                "question_text_quiz": full_text[i],
                "answer_text_quiz": full_text[i+1]
            })
    return qa_pairs

# 3. Estilização CSS (Inspirada na sua imagem)
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .question-box {
        background-color: #DDEBF7;
        padding: 30px;
        border: 2px solid #000;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        color: #000;
        margin-bottom: 20px;
        border-radius: 5px;
    }
    .timer-rect {
        background-color: #BFBFBF;
        color: white;
        padding: 10px 40px;
        font-size: 40px;
        font-weight: bold;
        display: inline-block;
        border-radius: 5px;
    }
    .hand-box {
        background-color: #FF0000;
        color: white;
        padding: 20px;
        font-size: 38px;
        font-weight: bold;
        text-align: center;
        border-radius: 10px;
        border: 3px solid #000;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# 4. Lógica de Autenticação
if 'auth' not in st.session_state:
    st.session_state.auth = {'logged': False, 'role': None, 'user': ""}

if not st.session_state.auth['logged']:
    st.title("🛡️ Login - Quiz Técnico")
    user_input = st.text_input("Seu Nome/Apelido")
    pass_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        # Login do Admin
        if pass_input == st.secrets["ADMIN_PASSWORD"]:
            new_master = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            supabase.table("game_state_quiz").update({"master_password_quiz": new_master}).eq("id_quiz", 1).execute()
            st.session_state.auth = {'logged': True, 'role': 'admin', 'user': user_input}
            st.rerun()
        else:
            # Login do Jogador (Busca senha mestre no banco)
            res = supabase.table("game_state_quiz").select("master_password_quiz").eq("id_quiz", 1).single().execute()
            if pass_input == res.data['master_password_quiz']:
                st.session_state.auth = {'logged': True, 'role': 'player', 'user': user_input}
                supabase.table("players_quiz").insert({"nickname_quiz": user_input}).execute()
                st.rerun()
            else:
                st.error("Senha incorreta ou Admin ainda não gerou acesso.")

# 5. Interface do Administrador
elif st.session_state.auth['role'] == 'admin':
    st.sidebar.title("⚙️ Painel Admin")
    state = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    
    st.sidebar.success(f"SENHA PARA JOGADORES: {state['master_password_quiz']}")
    
    # Upload do Arquivo Word
    uploaded_docx = st.sidebar.file_uploader("Carregar Perguntas (.docx)", type="docx")
    if uploaded_docx and st.sidebar.button("💾 Salvar Perguntas no Banco"):
        qa_data = parse_word_file(uploaded_docx)
        supabase.table("questions_quiz").delete().neq("id_quiz", 0).execute() # Limpa anteriores
        supabase.table("questions_quiz").insert(qa_data).execute()
        st.sidebar.info(f"{len(qa_data)} questões salvas!")

    # Controles do Jogo
    tempo_def = st.sidebar.number_input("Tempo (segundos)", value=15)
    pergunta_idx = st.sidebar.number_input("Índice da Pergunta", value=0, min_value=0)
    
    if st.sidebar.button("🚀 START (Iniciar Tempo)"):
        supabase.table("game_state_quiz").update({
            "is_active_quiz": True,
            "timer_duration_quiz": tempo_def,
            "current_question_index_quiz": pergunta_idx,
            "show_answer_quiz": False,
            "start_time_quiz": int(time.time())
        }).eq("id_quiz", 1).execute()

    if st.sidebar.button("✅ REVELAR RESPOSTA"):
        supabase.table("game_state_quiz").update({"show_answer_quiz": True, "is_active_quiz": False}).eq("id_quiz", 1).execute()

    # Gerenciar Jogadores
    st.sidebar.divider()
    st.sidebar.subheader("Jogadores Online")
    players = supabase.table("players_quiz").select("*").execute().data
    for p in players:
        if st.sidebar.button(f"Remover {p['nickname_quiz']}"):
            supabase.table("players_quiz").delete().eq("id_quiz", p['id_quiz']).execute()
            st.rerun()

# 6. Tela Principal do Jogo (Visível para Admin e Jogadores)
if st.session_state.auth['logged']:
    state = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    questions = supabase.table("questions_quiz").select("*").order("id_quiz").execute().data
    
    if questions and state['current_question_index_quiz'] < len(questions):
        q_atual = questions[state['current_question_index_quiz']]
        
        # Cabeçalho igual à imagem
        st.markdown('<h2 style="text-align:center; color:#A52A2A;">TESTE DE CONHECIMENTO DO PROCESSO DE FABRICAÇÃO DA WLI</h2>', unsafe_allow_html=True)
        
        # Caixa da Pergunta
        st.markdown(f'<div class="question-box">{q_atual["question_text_quiz"]}</div>', unsafe_allow_html=True)
        
        # Lógica do Cronômetro
        if state['is_active_quiz']:
            tempo_passado = int(time.time()) - state['start_time_quiz']
            tempo_restante = max(0, state['timer_duration_quiz'] - tempo_passado)
            
            col_t1, col_t2, col_t3 = st.columns([1,1,1])
            with col_t2:
                st.markdown(f'<div class="timer-rect">{tempo_restante}</div>', unsafe_allow_html=True)
            
            # Se o tempo acabar, mostra a mão
            if tempo_restante == 0:
                st.markdown('<div class="hand-box">✋ LEVANTE A MÃO E RESPONDA!</div>', unsafe_allow_html=True)
        
        # Mostrar Resposta
        if state['show_answer_quiz']:
            st.success(f"**RESPOSTA:** {q_atual['answer_text_quiz']}")
    else:
        st.warning("Aguardando o Admin iniciar ou carregar as perguntas.")
