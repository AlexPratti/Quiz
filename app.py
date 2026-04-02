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
url = st.secrets["URL_SUPABASE"]
key = st.secrets["KEY_SUPABASE"]
supabase = create_client(url, key)

# Mantemos o refresh de 2s para sincronizar as ações do Admin com os Jogadores
st_autorefresh(interval=2000, key="frequencia_quiz")

# --- 3. FUNÇÃO PARA LER O WORD ---
def parse_word_file(file):
    doc = Document(file)
    full_text =
    qa_pairs = []
    for i in range(0, len(full_text), 2):
        if i + 1 < len(full_text):
            qa_pairs.append({
                "question_text_quiz": full_text[i],
                "answer_text_quiz": full_text[i+1]
            })
    return qa_pairs

# --- 4. ESTILO CSS ---
st.markdown("""
    <style>
    .pergunta-box {
        background-color: #DDEBF7;
        padding: 40px;
        border: 3px solid #4472C4;
        text-align: center;
        font-size: 32px;
        font-weight: bold;
        color: #003366; /* Azul Escuro */
        border-radius: 12px;
        margin-bottom: 20px;
    }
    #timer-container {
        background-color: #7F7F7F;
        color: white;
        padding: 15px;
        font-size: 60px;
        text-align: center;
        font-weight: bold;
        width: 180px;
        margin: 20px auto;
        border-radius: 10px;
    }
    .mao-alerta {
        background-color: #FF0000;
        color: white;
        padding: 25px;
        text-align: center;
        font-size: 38px;
        font-weight: bold;
        border: 5px solid #000;
        border-radius: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = {'logged': False, 'role': None}

if not st.session_state.auth['logged']:
    st.title("🔑 Quiz Técnico")
    nome = st.text_input("Nome/Apelido")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == st.secrets["ADMIN_PASSWORD"]:
            nova_pwd = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            supabase.table("game_state_quiz").update({"master_password_quiz": nova_pwd}).eq("id_quiz", 1).execute()
            st.session_state.auth = {'logged': True, 'role': 'admin'}
            st.rerun()
        else:
            res = supabase.table("game_state_quiz").select("master_password_quiz").eq("id_quiz", 1).single().execute()
            if senha == res.data['master_password_quiz']:
                st.session_state.auth = {'logged': True, 'role': 'player'}
                supabase.table("players_quiz").insert({"nickname_quiz": nome}).execute()
                st.rerun()
            else:
                st.error("Senha inválida.")

# --- 6. PAINEL ADMIN ---
elif st.session_state.auth['role'] == 'admin':
    st.sidebar.title("🛠️ ADMIN")
    estado = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    st.sidebar.warning(f"SENHA JOGADORES: {estado['master_password_quiz']}")
    
    arq = st.sidebar.file_uploader("Word (.docx)", type="docx")
    if arq and st.sidebar.button("Carregar Questões"):
        dados = parse_word_file(arq)
        supabase.table("questions_quiz").delete().neq("id_quiz", 0).execute()
        supabase.table("questions_quiz").insert(dados).execute()
        st.sidebar.success("OK!")

    st.sidebar.divider()
    idx_atual = estado['current_question_index_quiz']
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("⬅️ Anterior"):
            supabase.table("game_state_quiz").update({"current_question_index_quiz": max(0, idx_atual-1), "show_answer_quiz": False, "is_active_quiz": False}).eq("id_quiz", 1).execute()
            st.rerun()
    with col2:
        if st.button("Próxima ➡️"):
            supabase.table("game_state_quiz").update({"current_question_index_quiz": idx_atual+1, "show_answer_quiz": False, "is_active_quiz": False}).eq("id_quiz", 1).execute()
            st.rerun()

    tempo_input = st.sidebar.number_input("Segundos", value=15)
    if st.sidebar.button("🚀 INICIAR CRONÔMETRO", use_container_width=True):
        # start_time_quiz salva o momento exato do clique em segundos (Unix Timestamp)
        supabase.table("game_state_quiz").update({
            "is_active_quiz": True, "timer_duration_quiz": tempo_input,
            "show_answer_quiz": False, "start_time_quiz": int(time.time())
        }).eq("id_quiz", 1).execute()

    if st.sidebar.button("✅ REVELAR RESPOSTA", use_container_width=True):
        supabase.table("game_state_quiz").update({"show_answer_quiz": True, "is_active_quiz": False}).eq("id_quiz", 1).execute()

# --- 7. TELA DO JOGO ---
if st.session_state.auth['logged']:
    st.markdown('<h2 style="text-align:center;">FABRICAÇÃO WLI</h2>', unsafe_allow_html=True)
    estado = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    perguntas = supabase.table("questions_quiz").select("*").order("id_quiz").execute().data
    
    if perguntas and estado['current_question_index_quiz'] < len(perguntas):
        p_obj = perguntas[estado['current_question_index_quiz']]
        st.markdown(f'<div class="pergunta-box">{p_obj["question_text_quiz"]}</div>', unsafe_allow_html=True)
        
        # LÓGICA DO CRONÔMETRO COM JAVASCRIPT (1 em 1 segundo)
        if estado['is_active_quiz']:
            duracao = estado['timer_duration_quiz']
            inicio = estado['start_time_quiz']
            
            # Script que faz a conta matemática no navegador do usuário
            st.markdown(f"""
                <div id="timer-container">--</div>
                <div id="mao-container"></div>

                <script>
                (function() {{
                    var duration = {duracao};
                    var startTime = {inicio};
                    var timerDisplay = document.getElementById('timer-container');
                    var maoContainer = document.getElementById('mao-container');

                    function updateTimer() {{
                        var now = Math.floor(Date.now() / 1000);
                        var elapsed = now - startTime;
                        var remaining = duration - elapsed;

                        if (remaining > 0) {{
                            timerDisplay.innerHTML = remaining;
                            maoContainer.innerHTML = "";
                        }} else {{
                            timerDisplay.innerHTML = "0";
                            maoContainer.innerHTML = '<div class="mao-alerta">✋ LEVANTE A MÃO E RESPONDA!</div>';
                            clearInterval(intervalo);
                        }}
                    }}
                    
                    var intervalo = setInterval(updateTimer, 1000);
                    updateTimer();
                }})();
                </script>
            """, unsafe_allow_html=True)
        
        if estado['show_answer_quiz']:
            st.success(f"**RESPOSTA:** {p_obj['answer_text_quiz']}")
