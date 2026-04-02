import streamlit as st
import streamlit.components.v1 as components
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

# Refresh de 2s para sincronizar os usuários com as ações do Admin
st_autorefresh(interval=2000, key="refresh_sincronizado")

# --- 3. FUNÇÃO DE LEITURA DO WORD (SIMPLIFICADA AO MÁXIMO) ---
def parse_word_file(file):
    documento = Document(file)
    texto_extraido = []
    
    for paragrafo in documento.paragraphs:
        conteudo = paragrafo.text.strip()
        if conteudo != "":
            texto_extraido.append(conteudo)
    
    lista_final = []
    # Pega Pares: i = Pergunta, i+1 = Resposta
    for i in range(0, len(texto_extraido), 2):
        if (i + 1) < len(texto_extraido):
            pergunta_txt = texto_extraido[i]
            resposta_txt = texto_extraido[i+1]
            bloco = {
                "question_text_quiz": pergunta_txt,
                "answer_text_quiz": resposta_txt
            }
            lista_final.append(bloco)
    return lista_final

# --- 4. ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .caixa-pergunta {
        background-color: #DDEBF7;
        padding: 40px;
        border: 3px solid #4472C4;
        text-align: center;
        font-size: 32px;
        font-weight: bold;
        color: #002060; /* Azul Escuro */
        border-radius: 15px;
        margin-bottom: 20px;
    }
    .alerta-mao {
        background-color: #C00000;
        color: white;
        padding: 25px;
        text-align: center;
        font-size: 40px;
        font-weight: bold;
        border: 5px solid #000;
        border-radius: 20px;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. LÓGICA DE LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = {'logged': False, 'role': None}

if not st.session_state.auth['logged']:
    st.title("🔑 Quiz Técnico WLI")
    u_nome = st.text_input("Apelido")
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
                st.error("Senha incorreta!")

# --- 6. PAINEL ADMIN ---
elif st.session_state.auth['role'] == 'admin':
    st.sidebar.title("ADMINISTRAÇÃO")
    state = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    st.sidebar.info(f"SENHA JOGADORES: {state['master_password_quiz']}")
    
    f_word = st.sidebar.file_uploader("Arquivo Word", type="docx")
    if f_word and st.sidebar.button("Carregar Questões"):
        dados_word = parse_word_file(f_word)
        supabase.table("questions_quiz").delete().neq("id_quiz", 0).execute()
        supabase.table("questions_quiz").insert(dados_word).execute()
        st.sidebar.success("OK!")

    st.sidebar.divider()
    idx = state['current_question_index_quiz']
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("⬅️ Anterior"):
            supabase.table("game_state_quiz").update({"current_question_index_quiz": max(0, idx-1), "show_answer_quiz": False, "is_active_quiz": False}).eq("id_quiz", 1).execute()
            st.rerun()
    with col2:
        if st.button("Próxima ➡️"):
            supabase.table("game_state_quiz").update({"current_question_index_quiz": idx+1, "show_answer_quiz": False, "is_active_quiz": False}).eq("id_quiz", 1).execute()
            st.rerun()

    t_set = st.sidebar.number_input("Tempo", value=15)
    if st.sidebar.button("🚀 START CRONÔMETRO", use_container_width=True):
        supabase.table("game_state_quiz").update({
            "is_active_quiz": True, "timer_duration_quiz": t_set,
            "show_answer_quiz": False, "start_time_quiz": int(time.time())
        }).eq("id_quiz", 1).execute()

    if st.sidebar.button("✅ VER RESPOSTA", use_container_width=True):
        supabase.table("game_state_quiz").update({"show_answer_quiz": True, "is_active_quiz": False}).eq("id_quiz", 1).execute()

# --- 7. TELA DO JOGO ---
if st.session_state.auth['logged']:
    st.markdown('<h2 style="text-align:center;">QUIZ VISITA TÉCNICA - WLI</h2>', unsafe_allow_html=True)
    
    g_res = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    q_res = supabase.table("questions_quiz").select("*").order("id_quiz").execute().data
    
    if q_res and g_res['current_question_index_quiz'] < len(q_res):
        item = q_res[g_res['current_question_index_quiz']]
        st.markdown(f'<div class="caixa-pergunta">{item["question_text_quiz"]}</div>', unsafe_allow_html=True)
        
        # --- CRONÔMETRO COM HTML COMPONENT (RESOLVE O PROBLEMA DO JS) ---
        if g_res['is_active_quiz']:
            dur = g_res['timer_duration_quiz']
            ini = g_res['start_time_quiz']
            
            timer_html = f"""
            <div id="timer-ui" style="
                background-color: #595959; color: white; padding: 15px; 
                font-size: 60px; text-align: center; font-family: sans-serif;
                font-weight: bold; width: 180px; margin: 0 auto; border-radius: 10px;
                border: 2px solid #000;">--</div>
            <div id="mao-ui"></div>

            <script>
                var duracao = {dur};
                var inicio = {ini};
                var display = document.getElementById('timer-ui');
                var mao = document.getElementById('mao-ui');

                function atualizar() {{
                    var agora = Math.floor(Date.now() / 1000);
                    var resto = duracao - (agora - inicio);

                    if (resto > 0) {{
                        display.innerHTML = resto;
                        mao.innerHTML = "";
                    }} else {{
                        display.innerHTML = "0";
                        display.style.backgroundColor = "#C00000";
                        mao.innerHTML = '<div style="background-color: #C00000; color: white; padding: 25px; text-align: center; font-size: 35px; font-weight: bold; border: 5px solid #000; border-radius: 20px; margin-top: 20px; font-family: sans-serif;">✋ LEVANTE A MÃO E RESPONDA!</div>';
                        clearInterval(loop);
                    }}
                }}
                var loop = setInterval(atualizar, 1000);
                atualizar();
            </script>
            """
            components.html(timer_html, height=250)
        
        if g_res['show_answer_quiz']:
            st.success(f"**RESPOSTA:** {item['answer_text_quiz']}")
    else:
        st.info("Aguardando ação do administrador...")
