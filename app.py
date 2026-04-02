import streamlit as st
from docx import Document
from supabase import create_client
import random
import string
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Quiz WLI", layout="wide")

# --- 2. CONEXÃO SUPABASE ---
url = st.secrets["URL_SUPABASE"]
key = st.secrets["KEY_SUPABASE"]
supabase = create_client(url, key)

# Atualiza a cada 2 segundos para sincronizar Admin e Jogadores
st_autorefresh(interval=2000, key="sync_quiz_wli")

# --- 3. FUNÇÃO DE LEITURA DO WORD (SEGURA CONTRA ERROS) ---
def parse_word_file(file):
    doc = Document(file)
    lista_de_texto = []
    
    # Extrai o texto linha por linha
    for p in doc.paragraphs:
        texto_limpo = p.text.strip()
        if texto_limpo != "":
            lista_de_texto.append(texto_limpo)
    
    qa_pairs = []
    # Pula de 2 em 2: Pergunta (i) e Resposta (i+1)
    for i in range(0, len(lista_de_texto), 2):
        if i + 1 < len(lista_de_texto):
            pergunta = lista_de_texto[i]
            resposta = lista_de_texto[i+1]
            dicionario = {
                "question_text_quiz": pergunta,
                "answer_text_quiz": resposta
            }
            qa_pairs.append(dicionario)
    return qa_pairs

# --- 4. ESTILO CSS (ALTA VISIBILIDADE) ---
st.markdown("""
    <style>
    .caixa-pergunta {
        background-color: #DDEBF7;
        padding: 40px;
        border: 4px solid #4472C4;
        text-align: center;
        font-size: 35px; /* Fonte Grande */
        font-weight: bold;
        color: #002060; /* AZUL ESCURO FORTE */
        border-radius: 15px;
        margin-bottom: 25px;
    }
    .display-cronometro {
        background-color: #595959;
        color: #FFFFFF;
        padding: 15px;
        font-size: 65px;
        text-align: center;
        font-weight: bold;
        width: 200px;
        margin: 20px auto;
        border-radius: 10px;
        border: 2px solid #000;
    }
    .alerta-mao {
        background-color: #C00000;
        color: white;
        padding: 25px;
        text-align: center;
        font-size: 40px;
        font-weight: bold;
        border: 6px solid #000;
        border-radius: 20px;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = {'logged': False, 'role': None}

if not st.session_state.auth['logged']:
    st.title("Acesso ao Quiz")
    u_nome = st.text_input("Seu Apelido")
    u_pass = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u_pass == st.secrets["ADMIN_PASSWORD"]:
            p_mestre = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            supabase.table("game_state_quiz").update({"master_password_quiz": p_mestre}).eq("id_quiz", 1).execute()
            st.session_state.auth = {'logged': True, 'role': 'admin'}
            st.rerun()
        else:
            res = supabase.table("game_state_quiz").select("master_password_quiz").eq("id_quiz", 1).single().execute()
            if u_pass == res.data['master_password_quiz']:
                st.session_state.auth = {'logged': True, 'role': 'player'}
                supabase.table("players_quiz").insert({"nickname_quiz": u_nome}).execute()
                st.rerun()
            else:
                st.error("Senha inválida.")

# --- 6. PAINEL ADMINISTRADOR ---
elif st.session_state.auth['role'] == 'admin':
    st.sidebar.title("ADMINISTRAÇÃO")
    state = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    st.sidebar.info(f"SENHA JOGADORES: {state['master_password_quiz']}")
    
    file_word = st.sidebar.file_uploader("Subir Word (.docx)", type="docx")
    if file_word and st.sidebar.button("Processar Word"):
        perguntas_word = parse_word_file(file_word)
        supabase.table("questions_quiz").delete().neq("id_quiz", 0).execute()
        supabase.table("questions_quiz").insert(perguntas_word).execute()
        st.sidebar.success("Perguntas Atualizadas!")

    st.sidebar.divider()
    idx_vazio = state['current_question_index_quiz']
    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.button("⬅️ Anterior"):
            supabase.table("game_state_quiz").update({"current_question_index_quiz": max(0, idx_vazio-1), "show_answer_quiz": False, "is_active_quiz": False}).eq("id_quiz", 1).execute()
            st.rerun()
    with c2:
        if st.button("Próxima ➡️"):
            supabase.table("game_state_quiz").update({"current_question_index_quiz": idx_vazio+1, "show_answer_quiz": False, "is_active_quiz": False}).eq("id_quiz", 1).execute()
            st.rerun()

    tempo_s = st.sidebar.number_input("Segundos", value=15)
    if st.sidebar.button("🚀 START CRONÔMETRO", use_container_width=True):
        supabase.table("game_state_quiz").update({
            "is_active_quiz": True, "timer_duration_quiz": tempo_s,
            "show_answer_quiz": False, "start_time_quiz": int(time.time())
        }).eq("id_quiz", 1).execute()

    if st.sidebar.button("✅ VER RESPOSTA", use_container_width=True):
        supabase.table("game_state_quiz").update({"show_answer_quiz": True, "is_active_quiz": False}).eq("id_quiz", 1).execute()

# --- 7. TELA DO JOGO (COM FÓRMULA MATEMÁTICA JS) ---
if st.session_state.auth['logged']:
    st.markdown('<h1 style="text-align:center;">QUIZ VISITA TÉCNICA - WLI</h1>', unsafe_allow_html=True)
    
    res_game = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    res_ques = supabase.table("questions_quiz").select("*").order("id_quiz").execute().data
    
    if res_ques and res_game['current_question_index_quiz'] < len(res_ques):
        q = res_ques[res_game['current_question_index_quiz']]
        st.markdown(f'<div class="caixa-pergunta">{q["question_text_quiz"]}</div>', unsafe_allow_html=True)
        
        # Cronômetro Matemático Injetado (Fórmula: Duração - (Agora - Início))
        if res_game['is_active_quiz']:
            t_duracao = res_game['timer_duration_quiz']
            t_inicio = res_game['start_time_quiz']
            
            st.markdown(f"""
                <div id="timer-box" class="display-cronometro">--</div>
                <div id="hand-area"></div>
                <script>
                (function() {{
                    var dur = {t_duracao};
                    var start = {t_inicio};
                    var display = document.getElementById('timer-box');
                    var hand = document.getElementById('hand-area');

                    function tick() {{
                        var agora = Math.floor(Date.now() / 1000);
                        var resto = dur - (agora - start);

                        if (resto > 0) {{
                            display.innerHTML = resto;
                            hand.innerHTML = "";
                        }} else {{
                            display.innerHTML = "0";
                            hand.innerHTML = '<div class="alerta-mao">✋ LEVANTE A MÃO E RESPONDA!</div>';
                            clearInterval(itv);
                        }}
                    }}
                    var itv = setInterval(tick, 1000);
                    tick();
                }})();
                </script>
            """, unsafe_allow_html=True)
        
        if res_game['show_answer_quiz']:
            st.markdown(f"""
                <div style="background-color: #D4EDDA; padding: 25px; border-radius: 10px; border: 2px solid #28A745; font-size: 28px; font-weight: bold; text-align: center; color: #155724;">
                    RESPOSTA: {q['answer_text_quiz']}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aguardando início...")
