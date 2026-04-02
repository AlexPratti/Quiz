import streamlit as st
import streamlit.components.v1 as components
from docx import Document
from supabase import create_client
import random
import string
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Quiz Técnico WLI", layout="wide")

# --- 2. CONEXÃO SUPABASE ---
url = st.secrets["URL_SUPABASE"]
key = st.secrets["KEY_SUPABASE"]
supabase = create_client(url, key)

# Refresh de 2s para sincronizar tudo em tempo real
st_autorefresh(interval=2000, key="refresh_sincronizado_wli")

# --- 3. FUNÇÃO DE LEITURA DO WORD (MANTIDA ORIGINAL) ---
def parse_word_file(file):
    documento = Document(file)
    texto_extraido = []
    for paragrafo in documento.paragraphs:
        conteudo = paragrafo.text.strip()
        if conteudo != "":
            texto_extraido.append(conteudo)
    
    lista_final = []
    for i in range(0, len(texto_extraido), 2):
        if (i + 1) < len(texto_extraido):
            lista_final.append({
                "question_text_quiz": texto_extraido[i],
                "answer_text_quiz": texto_extraido[i+1]
            })
    return lista_final

# --- 4. ESTILIZAÇÃO CSS (MANTIDA ORIGINAL COM ALTA VISIBILIDADE) ---
st.markdown("""
    <style>
    .caixa-pergunta {
        background-color: #DDEBF7;
        padding: 40px;
        border: 4px solid #4472C4;
        text-align: center;
        font-size: 35px;
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
    .contador-jogadores {
        background-color: #4472C4;
        color: white;
        padding: 10px;
        text-align: center;
        border-radius: 8px;
        font-weight: bold;
        font-size: 18px;
        margin-top: 10px;
        border: 1px solid #000;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. LÓGICA DE LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = {'logged': False, 'role': None, 'id': None}
if 'show_players_list' not in st.session_state:
    st.session_state.show_players_list = False

if not st.session_state.auth['logged']:
    st.title("🔑 Quiz: Entre no Jogo!")
    u_nome = st.text_input("Apelido")
    u_pass = st.text_input("Senha", type="password")
    
    if st.button("Entrar no Jogo"):
        if u_pass == st.secrets["ADMIN_PASSWORD"]:
            nova_pwd = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            supabase.table("game_state_quiz").update({"master_password_quiz": nova_pwd}).eq("id_quiz", 1).execute()
            # Admin ao entrar limpa a mesa para nova sessão
            supabase.table("players_quiz").delete().neq("id_quiz", 0).execute()
            st.session_state.auth = {'logged': True, 'role': 'admin', 'id': 'admin'}
            st.rerun()
        else:
            res = supabase.table("game_state_quiz").select("master_password_quiz").eq("id_quiz", 1).single().execute()
            if u_pass == res.data['master_password_quiz']:
                # Insere jogador e guarda o ID (sem erro de nome duplicado agora)
                p_ins = supabase.table("players_quiz").insert({"nickname_quiz": u_nome}).execute()
                st.session_state.auth = {'logged': True, 'role': 'player', 'id': p_ins.data[0]['id_quiz']}
                st.rerun()
            else:
                st.error("Senha incorreta ou Admin offline!")

# --- 6. INTERFACE LOGADA ---
else:
    # --- VERIFICAÇÃO DE EXPULSÃO (Sincroniza Jogadores com a saída do Admin) ---
    if st.session_state.auth['role'] == 'player':
        check_db = supabase.table("players_quiz").select("id_quiz").eq("id_quiz", st.session_state.auth['id']).execute()
        if not check_db.data:
            st.session_state.auth = {'logged': False, 'role': None, 'id': None}
            st.rerun()

    # --- BARRA LATERAL (SIDEBAR) ---
    st.sidebar.title("🎮 MENU DO QUIZ")
    
    # Botão Sair com função de expulsão geral para o Admin
    if st.sidebar.button("🚪 SAIR DO JOGO", use_container_width=True):
        if st.session_state.auth['role'] == 'admin':
            # Admin sai e remove TODOS os jogadores do banco
            supabase.table("players_quiz").delete().neq("id_quiz", 0).execute()
        else:
            # Jogador sai e remove apenas ele mesmo
            supabase.table("players_quiz").delete().eq("id_quiz", st.session_state.auth['id']).execute()
        
        st.session_state.auth = {'logged': False, 'role': None, 'id': None}
        st.rerun()

    st.sidebar.divider()

    if st.session_state.auth['role'] == 'admin':
        state = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
        st.sidebar.info(f"SENHA JOGADORES: {state['master_password_quiz']}")
        
        # Upload Word
        f_word = st.sidebar.file_uploader("Arquivo Word", type="docx")
        if f_word and st.sidebar.button("📤 Carregar Questões"):
            dados_word = parse_word_file(f_word)
            supabase.table("questions_quiz").delete().neq("id_quiz", 0).execute()
            supabase.table("questions_quiz").insert(dados_word).execute()
            st.sidebar.success("Questões Atualizadas!")

        st.sidebar.divider()
        
        # Gestão de Jogadores
        res_players = supabase.table("players_quiz").select("*").execute()
        players_data = res_players.data
        
        if st.sidebar.button("📋 JOGADORES"):
            st.session_state.show_players_list = not st.session_state.show_players_list

        if st.session_state.show_players_list:
            for p in players_data:
                col_p1, col_p2 = st.sidebar.columns([3, 1])
                col_p1.text(f"👤 {p['nickname_quiz']}")
                if col_p2.button("❌", key=f"del_{p['id_quiz']}"):
                    supabase.table("players_quiz").delete().eq("id_quiz", p['id_quiz']).execute()
                    st.rerun()

        st.sidebar.markdown(f'<div class="contador-jogadores">JOGADORES ON-LINE: {len(players_data)}</div>', unsafe_allow_html=True)
        st.sidebar.divider()

        # Navegação
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

    # --- 7. TELA PRINCIPAL DO JOGO ---
    st.markdown('<h1 style="text-align:center; color:#333;">TESTE SEUS CONHECIMENTOS</h1>', unsafe_allow_html=True)
    
    g_res = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    q_res = supabase.table("questions_quiz").select("*").order("id_quiz").execute().data
    
    if q_res and g_res['current_question_index_quiz'] < len(q_res):
        item = q_res[g_res['current_question_index_quiz']]
        st.markdown(f'<div class="caixa-pergunta">{item["question_text_quiz"]}</div>', unsafe_allow_html=True)
        
        if g_res['is_active_quiz']:
            timer_html = f"""
            <div id="timer-ui" class="display-cronometro" style="background-color:#595959; color:white; padding:15px; font-size:60px; text-align:center; font-family:sans-serif; font-weight:bold; width:180px; margin:0 auto; border-radius:10px; border:2px solid #000;">--</div>
            <div id="mao-ui"></div>
            <script>
                var dur = {g_res['timer_duration_quiz']}; var ini = {g_res['start_time_quiz']};
                var disp = document.getElementById('timer-ui'); var mao = document.getElementById('mao-ui');
                function upd() {{
                    var ag = Math.floor(Date.now() / 1000); var res = dur - (ag - ini);
                    if (res > 0) {{ disp.innerHTML = res; mao.innerHTML = ""; }}
                    else {{
                        disp.innerHTML = "0"; disp.style.backgroundColor = "#C00000";
                        mao.innerHTML = '<div class="alerta-mao" style="background-color:#C00000; color:white; padding:25px; text-align:center; font-size:35px; font-weight:bold; border:5px solid #000; border-radius:20px; margin-top:20px; font-family:sans-serif;">✋ LEVANTE A MÃO E RESPONDA!</div>';
                        clearInterval(lp);
                    }}
                }}
                var lp = setInterval(upd, 1000); upd();
            </script>
            """
            components.html(timer_html, height=250)
        
        if g_res['show_answer_quiz']:
            st.success(f"**RESPOSTA:** {item['answer_text_quiz']}")
    else:
        st.info("Aguardando o Administrador carregar as questões ou iniciar o jogo.")
