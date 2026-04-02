import streamlit as st
import streamlit.components.v1 as components
from docx import Document
from supabase import create_client
import random
import string
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO DA PÁGINA (MANTIDA ORIGINAL) ---
st.set_page_config(page_title="Quiz Técnico WLI", layout="wide")

# --- 2. CONEXÃO SUPABASE (USANDO SEUS SECRETS) ---
url = st.secrets["URL_SUPABASE"]
key = st.secrets["KEY_SUPABASE"]
supabase = create_client(url, key)

# Refresh de 2s para sincronização constante entre Admin e Jogadores
st_autorefresh(interval=2000, key="sync_final_original_wli")

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

# --- 4. ESTILIZAÇÃO CSS (MANTIDA ORIGINALIDADE E ALTA VISIBILIDADE) ---
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

# --- 5. LÓGICA DE LOGIN E SESSÃO ---
if 'auth' not in st.session_state:
    st.session_state.auth = {'logged': False, 'role': None, 'id': None}
if 'show_players_list' not in st.session_state:
    st.session_state.show_players_list = False
if 'pool_questoes' not in st.session_state:
    st.session_state.pool_questoes = []

if not st.session_state.auth['logged']:
    st.title("🔑 Quiz Técnico WLI")
    u_nome = st.text_input("Apelido")
    u_pass = st.text_input("Senha", type="password")
    
    if st.button("Entrar no Jogo"):
        if u_pass == st.secrets["ADMIN_PASSWORD"]:
            nova_pwd = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            supabase.table("game_state_quiz").update({"master_password_quiz": nova_pwd}).eq("id_quiz", 1).execute()
            supabase.table("players_quiz").delete().neq("id_quiz", 0).execute()
            st.session_state.auth = {'logged': True, 'role': 'admin', 'id': 'admin'}
            st.rerun()
        else:
            res = supabase.table("game_state_quiz").select("master_password_quiz").eq("id_quiz", 1).single().execute()
            if u_pass == res.data['master_password_quiz']:
                p_ins = supabase.table("players_quiz").insert({"nickname_quiz": u_nome}).execute()
                st.session_state.auth = {'logged': True, 'role': 'player', 'id': p_ins.data['id_quiz']}
                st.rerun()
            else:
                st.error("Senha incorreta!")

# --- 6. INTERFACE LOGADA ---
else:
    # Verificação de expulsão automática do jogador
    if st.session_state.auth['role'] == 'player':
        check_db = supabase.table("players_quiz").select("id_quiz").eq("id_quiz", st.session_state.auth['id']).execute()
        if not check_db.data:
            st.session_state.auth = {'logged': False, 'role': None, 'id': None}
            st.rerun()

    # --- BARRA LATERAL (SIDEBAR) ---
    st.sidebar.title("🎮 MENU DO QUIZ")
    
    if st.sidebar.button("🚪 SAIR E ENCERRAR TUDO", use_container_width=True):
        if st.session_state.auth['role'] == 'admin':
            supabase.table("players_quiz").delete().neq("id_quiz", 0).execute()
        else:
            supabase.table("players_quiz").delete().eq("id_quiz", st.session_state.auth['id']).execute()
        st.session_state.auth = {'logged': False, 'role': None, 'id': None}
        st.rerun()

    st.sidebar.divider()

    if st.session_state.auth['role'] == 'admin':
        state = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
        st.sidebar.info(f"SENHA JOGADORES: {state['master_password_quiz']}")
        
        f_word = st.sidebar.file_uploader("Arquivo Word", type="docx")
        if f_word and st.sidebar.button("📤 CARREGAR QUESTÕES"):
            dados_word = parse_word_file(f_word)
            supabase.table("questions_quiz").delete().neq("id_quiz", 0).execute()
            res_db = supabase.table("questions_quiz").insert(dados_word).execute()
            # Inicializa o pool de sorteio com os IDs do banco
            st.session_state.pool_questoes = [q['id_quiz'] for q in res_db.data]
            # Reseta estado do jogo: -1 indica início
            supabase.table("game_state_quiz").update({"current_question_index_quiz": -1, "is_active_quiz": False, "show_answer_quiz": False}).eq("id_quiz", 1).execute()
            st.sidebar.success(f"{len(dados_word)} questões carregadas!")
            st.rerun()

        st.sidebar.divider()
        
        # Gestão de Jogadores
        res_players = supabase.table("players_quiz").select("*").execute()
        players_data = res_players.data
        if st.sidebar.button("📋 JOGADORES"):
            st.session_state.show_players_list = not st.session_state.show_players_list

        if st.session_state.show_players_list:
            for p in players_data:
                col_p1, col_p2 = st.sidebar.columns()
                col_p1.text(f"👤 {p['nickname_quiz']}")
                if col_p2.button("❌", key=f"del_{p['id_quiz']}"):
                    supabase.table("players_quiz").delete().eq("id_quiz", p['id_quiz']).execute()
                    st.rerun()

        st.sidebar.markdown(f'<div class="contador-jogadores">JOGADORES ON-LINE: {len(players_data)}</div>', unsafe_allow_html=True)
        st.sidebar.divider()

        # NAVEGAÇÃO: BOTÃO PRÓXIMA COM SORTEIO ALEATÓRIO E CRONÔMETRO AUTOMÁTICO
        t_padrao = st.sidebar.number_input("Tempo de Prova", value=15)
        
        if st.sidebar.button("🎲 PRÓXIMA PERGUNTA ALEATÓRIA", use_container_width=True):
            if st.session_state.pool_questoes:
                # Sorteia ID, remove do pool e atualiza o banco
                id_sorteado = random.choice(st.session_state.pool_questoes)
                st.session_state.pool_questoes.remove(id_sorteado)
                
                supabase.table("game_state_quiz").update({
                    "current_question_index_quiz": id_sorteado,
                    "is_active_quiz": True,
                    "show_answer_quiz": False,
                    "timer_duration_quiz": t_padrao,
                    "start_time_quiz": int(time.time())
                }).eq("id_quiz", 1).execute()
            else:
                # Código -2 indica que o quiz acabou
                supabase.table("game_state_quiz").update({"current_question_index_quiz": -2}).eq("id_quiz", 1).execute()
            st.rerun()

        # RESET: Interrompe a exibição do cronômetro da tela
        if st.sidebar.button("🔄 RESET CRONÔMETRO", use_container_width=True):
            supabase.table("game_state_quiz").update({"is_active_quiz": False, "show_answer_quiz": False}).eq("id_quiz", 1).execute()
            st.rerun()

        if st.sidebar.button("✅ VER RESPOSTA", use_container_width=True):
            supabase.table("game_state_quiz").update({"show_answer_quiz": True, "is_active_quiz": False}).eq("id_quiz", 1).execute()
            st.rerun()

    # --- 7. TELA DO JOGO (COM CRONÔMETRO MATEMÁTICO JS) ---
    st.markdown('<h1 style="text-align:center; color:#333;">QUIZ VISITA TÉCNICA - WLI</h1>', unsafe_allow_html=True)
    
    g_res = supabase.table("game_state_quiz").select("*").eq("id_quiz", 1).single().execute().data
    
    if g_res['current_question_index_quiz'] == -2:
        st.balloons()
        st.success("🎉 TODAS AS PERGUNTAS FORAM RESPONDIDAS!")
    elif g_res['current_question_index_quiz'] != -1:
        # Busca a pergunta sorteada pelo ID específico
        q_data = supabase.table("questions_quiz").select("*").eq("id_quiz", g_res['current_question_index_quiz']).single().execute().data
        
        if q_data:
            st.markdown(f'<div class="caixa-pergunta">{q_data["question_text_quiz"]}</div>', unsafe_allow_html=True)
            
            if g_res['is_active_quiz']:
                timer_html = f"""
                <div id="t-ui" style="background:#595959; color:white; padding:15px; font-size:60px; text-align:center; font-family:sans-serif; font-weight:bold; width:180px; margin:0 auto; border-radius:10px; border:2px solid #000;">--</div>
                <div id="m-ui"></div>
                <script>
                    var dur = {g_res['timer_duration_quiz']}; var ini = {g_res['start_time_quiz']};
                    var d_el = document.getElementById('t-ui'); var m_el = document.getElementById('m-ui');
                    function tick() {{
                        var agora = Math.floor(Date.now() / 1000); var resto = dur - (agora - ini);
                        if (resto > 0) {{ d_el.innerHTML = resto; m_el.innerHTML = ""; }}
                        else {{
                            d_el.innerHTML = "0"; d_el.style.background = "#C00000";
                            m_el.innerHTML = '<div style="background:#C00000; color:white; padding:25px; text-align:center; font-size:35px; font-weight:bold; border:5px solid #000; border-radius:20px; margin-top:20px; font-family:sans-serif;">✋ LEVANTE A MÃO E RESPONDA!</div>';
                            clearInterval(loop);
                        }}
                    }}
                    var loop = setInterval(tick, 1000); tick();
                </script>
                """
                components.html(timer_html, height=250)
            
            if g_res['show_answer_quiz']:
                st.success(f"**RESPOSTA:** {q_data['answer_text_quiz']}")
    else:
        st.info("Aguardando o Administrador iniciar o Quiz.")
