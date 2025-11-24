import socket
import getpass
import json
import sys

# ==================== CONFIGURAÇÕES DE CONEXÃO ====================
# IMPORTANTE: Altere este IP para o endereço da máquina que está rodando o servidor_pim.py!
HOST_SERVIDOR = '26.113.61.226'  # TROCAR ESTE IP
PORTA_SERVIDOR = 50007

# ==================== FUNÇÕES DE COMUNICAÇÃO (CLIENTE) ====================
def enviar_comando(sock, comando):
    """Envia um comando formatado para o servidor e recebe a resposta."""
    try:
        # Protocolo de envio: [TAMANHO: 10 bytes][MENSAGEM]
        comando_bytes = comando.encode('utf-8')
        tamanho = f"{len(comando_bytes):<10}" # '123      '
        sock.sendall(tamanho.encode('utf-8') + comando_bytes)
        
        # Protocolo de recebimento: [TAMANHO: 10 bytes][MENSAGEM]
        tamanho_bytes = sock.recv(10)
        if not tamanho_bytes:
            return "❌ ERRO: Servidor desconectou (cabeçalho)."
            
        tamanho_msg = int(tamanho_bytes.decode('utf-8').strip())
        
        # Recebe a mensagem completa com base no tamanho
        dados_recebidos = b""
        while len(dados_recebidos) < tamanho_msg:
            # Pede o restante dos dados (ou 4096 bytes)
            parte = sock.recv(min(tamanho_msg - len(dados_recebidos), 4096))
            if not parte:
                return "❌ ERRO: Servidor desconectou (dados)."
            dados_recebidos += parte
            
        return dados_recebidos.decode('utf-8')
        
    except ConnectionResetError:
        print("\n❌ ERRO FATAL: A conexão com o servidor foi perdida.")
        sys.exit() # Fecha o cliente
    except Exception as e:
        print(f"\n❌ ERRO de comunicação: {e}")
        sys.exit()

def imprimir_resposta(resposta_str, cache_key=None, cache_ref=None):
    """
    Formata e imprime a resposta do servidor.
    Se 'cache_key' e 'cache_ref' forem fornecidos, armazena o JSON no cache.
    """
    print("\n<<< Resposta do Servidor >>>")
    try:
        if resposta_str.startswith('[') and resposta_str.endswith(']'):
            dados = json.loads(resposta_str)
            if not dados:
                print("(Nenhum item encontrado/retornado)")
            
            # Salva no cache se os parâmetros foram passados
            if cache_key and cache_ref is not None:
                # Cria um dicionário de ID -> item para busca rápida
                cache_ref[cache_key] = {item.get('id'): item for item in dados}
                # Não imprime o "cache atualizado" para não poluir a tela
                # print(f"(Lista de '{cache_key}' atualizada no cache.)")

            # Imprime os dados formatados
            for item in dados:
                print("---")
                info = []
                for k, v in item.items():
                    if k.lower() != 'senha': # Nunca imprimir senhas
                        info.append(f"{k.capitalize()}: {v}")
                print(" | ".join(info))
        else:
            print(resposta_str) # Imprime mensagens de SUCESSO, ERRO, ou relatórios
    except json.JSONDecodeError:
        print(resposta_str) # Se não for JSON, imprime como texto
    print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

# ==================== FUNÇÕES DE INPUT (SÓ NO CLIENTE) ====================
def linha(tam=60): return "-" * tam
def header(title):
    print("\n" + linha(70))
    print(f"📚  {title}")
    print(linha(70))

def input_int(prompt, min_val=None, max_val=None, allow_empty=False):
    while True:
        v = input(prompt).strip()
        if allow_empty and v == "": return None
        if not v.isdigit():
            print("Digite um número válido.")
            continue
        n = int(v)
        if min_val is not None and n < min_val:
            print(f"Valor mínimo: {min_val}")
            continue
        if max_val is not None and n > max_val:
            print(f"Valor máximo: {max_val}")
            continue
        return n

def input_float(prompt, min_val=None, max_val=None, allow_empty=False):
    while True:
        v = input(prompt).strip()
        if allow_empty and v == "": return None
        try:
            f = float(v.replace(",", "."))
        except:
            print("Digite um número válido (use . ou ,).")
            continue
        if min_val is not None and f < min_val:
            print(f"Valor mínimo: {min_val}")
            continue
        if max_val is not None and f > max_val:
            print(f"Valor máximo: {max_val}")
            continue
        return f

def confirma(prompt="Confirmar? (s/n): "):
    r = input(prompt).strip().lower()
    return r in ("s", "y")

# ==================== NOVAS FUNÇÕES DE CACHE (CLIENTE) ====================

def buscar_e_listar(sock, cache_ref, cache_key, comando_lista):
    """
    Busca a lista de itens (ex: 'alunos') no servidor,
    exibe de forma limpa, e armazena no cache.
    Retorna True se o cache estiver pronto, False se falhar.
    """
    print(f"\nBuscando lista de '{cache_key}' no servidor...")
    resposta_lista = enviar_comando(sock, comando_lista)
    
    # Limpa a tela de Resposta do Servidor para uma listagem mais limpa
    print("\n" + linha(70))
    
    try:
        if resposta_lista.startswith('[') and resposta_lista.endswith(']'):
            dados = json.loads(resposta_lista)
            if not dados:
                print(f"Nenhum {cache_key} encontrado.")
                cache_ref[cache_key] = {} # Armazena um cache vazio
                return False

            # Armazena no cache como um dicionário (ID -> item)
            cache_ref[cache_key] = {item.get('id'): item for item in dados}
            
            # Imprime a lista formatada (como na sua foto)
            header(cache_key.upper())
            for item in dados:
                id_str = str(item.get('id', ''))
                mat_str = item.get('matricula', '')
                nome_str = item.get('nome', 'N/D')
                
                if mat_str: # Formato para Alunos/Professores
                    print(f"{id_str.ljust(3)} - {mat_str.ljust(10)} - {nome_str}")
                else: # Formato para Turmas/Atividades
                    # Adapta para a nova estrutura de 'listar_turmas'
                    alunos_count = item.get('alunos', 0)
                    atv_count = item.get('atividades', 0)
                    print(f"{id_str.ljust(3)} - {nome_str.ljust(15)} (Alunos: {alunos_count}, Atividades: {atv_count})")
            
            print(linha(70))
            return True # Sucesso
        else:
            # Se não for uma lista (ex: "Sem notas registradas")
            print(resposta_lista)
            return False
    except json.JSONDecodeError:
        print(f"ERRO: Resposta inesperada do servidor:\n{resposta_lista}") # Imprime a string de erro
        return False
        
def obter_item_cacheado(cache_ref, cache_key, item_id_str):
    """Busca um item específico no cache pelo seu ID."""
    try:
        item_id = int(item_id_str)
        if cache_key in cache_ref:
            return cache_ref[cache_key].get(item_id)
    except:
        pass
    return None

def invalidar_cache(cache_ref, cache_key):
    """Remove um item do cache para forçar a atualização na próxima vez."""
    if cache_key in cache_ref:
        del cache_ref[cache_key]
        print(f"(Cache de '{cache_key}' invalidado.)")

# ==================== MENUS (SÓ NO CLIENTE) ====================
# ... (Funções de menu permanecem as mesmas) ...
def menu_acesso():
    header("ACESSO AO SISTEMA - Política de Privacidade (LGPD)")
    print("1. Cadastrar professor")
    print("2. Login")
    print("0. Sair")
    return input("Escolha: ").strip()

def menu_principal(nome_prof):
    header(f"SISTEMA ESCOLAR - Professor: {nome_prof}")
    print("1. Gerenciar Alunos")
    print("2. Gerenciar Turmas")
    print("3. Gerenciar Atividades e Notas")
    print("4. Gerenciar Relatórios e PDFs")
    print("5. Logout")
    print("0. Sair")
    return input("Escolha: ").strip()

def menu_professores_ui():
    header("PROFESSORES")
    print("1. Listar professores")
    print("2. Cadastrar professor (só disponível na tela de Acesso)")
    print("3. Editar professor")
    print("4. Remover professor")
    print("0. Voltar")
    return input("Escolha: ").strip()

def menu_alunos_ui():
    header("ALUNOS")
    print("1. Listar alunos")
    print("2. Cadastrar aluno")
    print("3. Editar aluno")
    print("4. Remover aluno")
    print("5. Buscar aluno")
    print("6. Ver turmas do aluno")
    print("0. Voltar")
    return input("Escolha: ").strip()

def menu_turmas_ui():
    header("TURMAS")
    print("1. Listar turmas")
    print("2. Cadastrar turma")
    print("3. Editar turma")
    print("4. Remover turma")
    print("5. Ver alunos da turma")
    print("6. Ver atividades da turma")
    print("7. Matricular aluno")
    print("8. Desmatricular aluno")
    print("0. Voltar")
    return input("Escolha: ").strip()

def menu_atividades_ui():
    header("ATIVIDADES E NOTAS")
    print("1. Listar atividades")
    print("2. Cadastrar atividade (com descrição)")
    print("3. Editar atividade")
    print("4. Remover atividade")
    print("5. Ver notas de uma atividade")
    print("6. Adicionar/editar nota")
    print("7. Remover nota")
    print("0. Voltar")
    return input("Escolha: ").strip()

def menu_relatorios_ui():
    header("RELATÓRIOS E PDFS")
    print("1. Gerar relatório (texto) por turma")
    print("2. Gerar relatório (PDF) por turma")
    print("3. Gerar boletins em PDF (um por aluno)")
    print("4. Relatório inteligente (médias por turma)")
    print("5. Melhor/pior aluno por turma")
    print("0. Voltar")
    return input("Escolha: ").strip()

# ==================== FLUXO PRINCIPAL (CLIENTE) ====================
def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST_SERVIDOR, PORTA_SERVIDOR))
            print(f"Conectado ao servidor em {HOST_SERVIDOR}:{PORTA_SERVIDOR}")
        except ConnectionRefusedError:
            print(f"❌ ERRO: Conexão recusada. Verifique se o 'servidor_pim.py' está online e o IP/Porta estão corretos.")
            sys.exit()

        # Loop Mestre que controla o fluxo Login -> Menu -> Login
        while True:
            nome_professor_logado = ""
            is_logged_in = False

            # Loop de Acesso
            while not is_logged_in:
                # ... (Lógica de Acesso - permanece a mesma) ...
                opc = menu_acesso()
                comando = None
                resposta = ""

                if opc == "1":
                    nome = input("Nome: ").strip()
                    matricula = input("Matrícula: ").strip()
                    senha = getpass.getpass("Senha: ")
                    if nome and matricula and senha:
                        comando = f"cadastrar_professor;{nome};{matricula};{senha}"
                    else:
                        print("❌ Todos os campos são obrigatórios.")
                
                elif opc == "2":
                    matricula = input("Matrícula: ").strip()
                    senha = getpass.getpass("Senha: ")
                    if matricula and senha:
                        comando = f"login_professor;{matricula};{senha}"
                    else:
                        print("❌ Matrícula e Senha são obrigatórios.")
                
                elif opc == "0":
                    print("Saindo...")
                    s.close()
                    return # Encerra a função main inteira
                else:
                    print("Opção inválida.")

                if comando:
                    resposta = enviar_comando(s, comando)
                    if resposta.startswith("SUCESSO_LOGIN:"):
                        nome_professor_logado = resposta.split(':', 1)[1] # Pega o nome
                        is_logged_in = True # Quebra o loop 'while not is_logged_in'
                        imprimir_resposta(f"✅ Login efetuado! Bem-vindo, Prof. {nome_professor_logado}.")
                    else:
                        imprimir_resposta(resposta) # Mostra SUCESSO ou ERRO

            # --- NOVO: Cache de dados para este login ---
            dados_cache = {}

            # Loop Principal (Logado)
            while is_logged_in:
                op = menu_principal(nome_professor_logado)
                comando = None
                resposta = ""

                # --- Gerenciar Alunos (LÓGICA ATUALIZADA) ---
                if op == "1":
                    while True:
                        sub = menu_alunos_ui()
                        comando = None
                        
                        if sub == "1": # LISTAR
                            if not buscar_e_listar(s, dados_cache, 'alunos', 'listar_alunos'):
                                continue

                        elif sub == "2": # CADASTRAR
                            nome = input("Nome: ").strip()
                            mat = input("Matrícula: ").strip()
                            if nome and mat: 
                                comando = f"cadastrar_aluno;{nome};{mat}"
                                resposta = enviar_comando(s, comando)
                                imprimir_resposta(resposta)
                                invalidar_cache(dados_cache, 'alunos')
                            else: 
                                print("❌ Nome e Matrícula obrigatórios.")

                        elif sub == "3": # EDITAR (Lógica CORRIGIDA)
                            if not buscar_e_listar(s, dados_cache, 'alunos', 'listar_alunos'):
                                continue
                            
                            aid_str = input("ID do aluno para editar (0 para cancelar): ")
                            if aid_str == "0": continue

                            a_atual = obter_item_cacheado(dados_cache, 'alunos', aid_str)
                            if not a_atual:
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue
                            
                            print(f"\nEditando Aluno: {a_atual['nome']}")
                            nome = input(f"Novo nome (atual: {a_atual['nome']}): ").strip()
                            mat = input(f"Nova matrícula (atual: {a_atual['matricula']}): ").strip()
                            
                            comando = f"editar_aluno;{aid_str};{nome};{mat}"
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)
                            invalidar_cache(dados_cache, 'alunos')

                        elif sub == "4": # REMOVER (Lógica CORRIGIDA)
                            if not buscar_e_listar(s, dados_cache, 'alunos', 'listar_alunos'):
                                continue
                            
                            aid_str = input("ID do aluno para remover (0 para cancelar): ")
                            if aid_str == "0": continue

                            a_atual = obter_item_cacheado(dados_cache, 'alunos', aid_str)
                            if not a_atual:
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue

                            if confirma(f"Remover aluno {a_atual['nome']}? (s/n): "):
                                comando = f"remover_aluno;{aid_str}"
                                resposta = enviar_comando(s, comando)
                                imprimir_resposta(resposta)
                                invalidar_cache(dados_cache, 'alunos')
                                invalidar_cache(dados_cache, 'turmas') # Aluno pode ter saído da turma

                        elif sub == "5": # BUSCAR
                            query = input("Buscar por nome ou matrícula: ").strip().lower()
                            if query: 
                                comando = f"buscar_aluno;{query}"
                                resposta = enviar_comando(s, comando)
                                imprimir_resposta(resposta) # Não salva busca no cache
                        
                        elif sub == "6": # VER TURMAS DO ALUNO (Lógica CORRIGIDA)
                            if not buscar_e_listar(s, dados_cache, 'alunos', 'listar_alunos'):
                                continue

                            aid_str = input("ID do aluno para ver turmas (0 para cancelar): ")
                            if aid_str == "0": continue

                            a_atual = obter_item_cacheado(dados_cache, 'alunos', aid_str)
                            if not a_atual:
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue
                            
                            print(f"Buscando turmas de {a_atual['nome']}...")
                            comando = f"ver_turmas_do_aluno;{aid_str}"
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)

                        elif sub == "0": 
                            break
                        else: 
                            print("Inválido.")

                # --- Gerenciar Turmas ---
                elif op == "2":
                    while True:
                        sub = menu_turmas_ui()
                        comando = None
                        
                        if sub == "1": # LISTAR
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                        
                        elif sub == "2": # CADASTRAR
                            nome = input("Nome da turma: ").strip()
                            if nome: 
                                comando = f"cadastrar_turma;{nome}"
                                resposta = enviar_comando(s, comando)
                                imprimir_resposta(resposta)
                                invalidar_cache(dados_cache, 'turmas')
                            
                        elif sub == "3": # EDITAR
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma para editar (0 para cancelar): ")
                            if tid_str == "0": continue
                            t_atual = obter_item_cacheado(dados_cache, 'turmas', tid_str)
                            if not t_atual:
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue

                            print(f"\nEditando Turma: {t_atual['nome']}")
                            nome = input(f"Novo nome (atual: {t_atual['nome']}): ").strip()
                            comando = f"editar_turma;{tid_str};{nome}"
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)
                            invalidar_cache(dados_cache, 'turmas')
                        
                        elif sub == "4": # REMOVER
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma para remover (0 para cancelar): ")
                            if tid_str == "0": continue
                            t_atual = obter_item_cacheado(dados_cache, 'turmas', tid_str)
                            if not t_atual:
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue

                            if confirma(f"Remover turma {t_atual['nome']}? (s/n): "):
                                comando = f"remover_turma;{tid_str}"
                                resposta = enviar_comando(s, comando)
                                imprimir_resposta(resposta)
                                invalidar_cache(dados_cache, 'turmas')
                                invalidar_cache(dados_cache, 'atividades')

                        elif sub == "5": # VER ALUNOS DA TURMA
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma (0 para cancelar): ")
                            if tid_str == "0": continue
                            if not obter_item_cacheado(dados_cache, 'turmas', tid_str):
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue
                            comando = f"ver_alunos_da_turma;{tid_str}"
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)

                        elif sub == "6": # VER ATIVIDADES DA TURMA
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma (0 para cancelar): ")
                            if tid_str == "0": continue
                            if not obter_item_cacheado(dados_cache, 'turmas', tid_str):
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue
                            comando = f"ver_atividades_da_turma;{tid_str}"
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)

                        elif sub == "7": # MATRICULAR ALUNO
                            if not buscar_e_listar(s, dados_cache, 'alunos', 'listar_alunos'):
                                continue
                            aid_str = input("ID do aluno (0 para cancelar): ")
                            if aid_str == "0": continue
                            if not obter_item_cacheado(dados_cache, 'alunos', aid_str):
                                imprimir_resposta("❌ ERRO: ID de aluno inválido.")
                                continue
                                
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma (0 para cancelar): ")
                            if tid_str == "0": continue
                            if not obter_item_cacheado(dados_cache, 'turmas', tid_str):
                                imprimir_resposta("❌ ERRO: ID de turma inválido.")
                                continue

                            comando = f"matricular_aluno_em_turma;{aid_str};{tid_str}"
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)
                            invalidar_cache(dados_cache, 'turmas')
                        
                        elif sub == "8": # DESMATRICULAR ALUNO
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma (0 para cancelar): ")
                            if tid_str == "0": continue
                            t_atual = obter_item_cacheado(dados_cache, 'turmas', tid_str)
                            if not t_atual:
                                imprimir_resposta("❌ ERRO: ID de turma inválido.")
                                continue
                            
                            # Lista alunos daquela turma
                            print(f"Buscando alunos da turma {t_atual['nome']}...")
                            comando_alunos = f"ver_alunos_da_turma;{tid_str}"
                            resposta_alunos = enviar_comando(s, comando_alunos)
                            imprimir_resposta(resposta_alunos) # Mostra os alunos

                            aid_str = input("ID do aluno para desmatricular (0 para cancelar): ")
                            if aid_str == "0": continue

                            if confirma("Desmatricular este aluno? (s/n):"):
                                comando = f"desmatricular_aluno;{tid_str};{aid_str}"
                                resposta = enviar_comando(s, comando)
                                imprimir_resposta(resposta)
                                invalidar_cache(dados_cache, 'turmas')

                        elif sub == "0": 
                            break
                        else: 
                            print("Inválido.")

                # --- Gerenciar Atividades/Notas ---
                elif op == "3":
                    while True:
                        sub = menu_atividades_ui()
                        comando = None
                        if sub == "1": # LISTAR
                            if not buscar_e_listar(s, dados_cache, 'atividades', 'listar_atividades'):
                                continue
                        
                        elif sub == "2": # CADASTRAR
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma (0 para cancelar): ")
                            if tid_str == "0": continue
                            if not obter_item_cacheado(dados_cache, 'turmas', tid_str):
                                imprimir_resposta("❌ ERRO: ID de turma inválido.")
                                continue

                            nome = input("Nome da atividade: ").strip()
                            descr = input("Descrição: ").strip()
                            if nome:
                                comando = f"cadastrar_atividade;{tid_str};{nome};{descr}"
                                resposta = enviar_comando(s, comando)
                                imprimir_resposta(resposta)
                                invalidar_cache(dados_cache, 'atividades')
                        
                        elif sub == "3": # EDITAR
                            if not buscar_e_listar(s, dados_cache, 'atividades', 'listar_atividades'):
                                continue
                            aid_str = input("ID da atividade para editar (0 para cancelar): ")
                            if aid_str == "0": continue
                            atv_atual = obter_item_cacheado(dados_cache, 'atividades', aid_str)
                            if not atv_atual:
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue
                                
                            print(f"\nEditando Atividade: {atv_atual['nome']}")
                            nome = input(f"Novo nome (atual: {atv_atual['nome']}): ").strip()
                            descr = input(f"Nova descrição (atual: {atv_atual.get('descricao', '')}): ").strip()
                            comando = f"editar_atividade;{aid_str};{nome};{descr}"
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)
                            invalidar_cache(dados_cache, 'atividades')

                        elif sub == "4": # REMOVER
                            if not buscar_e_listar(s, dados_cache, 'atividades', 'listar_atividades'):
                                continue
                            aid_str = input("ID da atividade para remover (0 para cancelar): ")
                            if aid_str == "0": continue
                            atv_atual = obter_item_cacheado(dados_cache, 'atividades', aid_str)
                            if not atv_atual:
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue

                            if confirma(f"Remover atividade {atv_atual['nome']}? (s/n):"):
                                comando = f"remover_atividade;{aid_str}"
                                resposta = enviar_comando(s, comando)
                                imprimir_resposta(resposta)
                                invalidar_cache(dados_cache, 'atividades')
                                invalidar_cache(dados_cache, 'turmas')

                        elif sub == "5": # VER NOTAS
                            if not buscar_e_listar(s, dados_cache, 'atividades', 'listar_atividades'):
                                continue
                            aid_str = input("ID da atividade (0 para cancelar): ")
                            if aid_str == "0": continue
                            if not obter_item_cacheado(dados_cache, 'atividades', aid_str):
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue
                            
                            comando = f"ver_notas_atividade;{aid_str}"
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)

                        elif sub == "6": # ADICIONAR/EDITAR NOTA
                            if not buscar_e_listar(s, dados_cache, 'atividades', 'listar_atividades'):
                                continue
                            atv_id_str = input("ID da atividade (0 para cancelar): ")
                            if atv_id_str == "0": continue
                            atv_atual = obter_item_cacheado(dados_cache, 'atividades', atv_id_str)
                            if not atv_atual:
                                imprimir_resposta("❌ ERRO: ID de atividade inválido.")
                                continue
                            
                            print(f"\nLançando notas para: {atv_atual['nome']}")
                            # Lista os alunos da turma desta atividade
                            comando_alunos = f"ver_alunos_da_turma;{atv_atual['turma_id']}"
                            resposta_alunos = enviar_comando(s, comando_alunos)
                            print("\nAlunos na turma:")
                            imprimir_resposta(resposta_alunos)

                            aluno_id_str = input("ID do aluno (0 para cancelar): ")
                            if aluno_id_str == "0": continue
                            
                            nota = input("Nota (0-10): ")
                            comando = f"adicionar_editar_nota;{atv_id_str};{aluno_id_str};{nota}"
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)

                        elif sub == "7": # REMOVER NOTA
                            if not buscar_e_listar(s, dados_cache, 'atividades', 'listar_atividades'):
                                continue
                            atv_id_str = input("ID da atividade (0 para cancelar): ")
                            if atv_id_str == "0": continue
                            atv_atual = obter_item_cacheado(dados_cache, 'atividades', atv_id_str)
                            if not atv_atual:
                                imprimir_resposta("❌ ERRO: ID de atividade inválido.")
                                continue
                            
                            print(f"\nRemovendo nota de: {atv_atual['nome']}")
                            comando_notas = f"ver_notas_atividade;{atv_id_str}"
                            resposta_notas = enviar_comando(s, comando_notas)
                            imprimir_resposta(resposta_notas) # Mostra as notas atuais

                            aluno_id_str = input("ID do aluno para remover nota (0 para cancelar): ")
                            if aluno_id_str == "0": continue
                            
                            if confirma("Remover esta nota? (s/n):"):
                                comando = f"remover_nota;{atv_id_str};{aluno_id_str}"
                                resposta = enviar_comando(s, comando)
                                imprimir_resposta(resposta)

                        elif sub == "0": 
                            break
                        else: 
                            print("Inválido.")
                
                # --- Gerenciar Relatórios ---
                elif op == "4":
                    while True:
                        sub = menu_relatorios_ui()
                        comando = None
                        if sub == "1":
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma (0 para cancelar): ")
                            if tid_str == "0": continue
                            if not obter_item_cacheado(dados_cache, 'turmas', tid_str):
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue
                            comando = f"gerar_relatorio_texto;{tid_str}"
                        
                        elif sub == "2":
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma (0 para cancelar): ")
                            if tid_str == "0": continue
                            if not obter_item_cacheado(dados_cache, 'turmas', tid_str):
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue
                            comando = f"gerar_relatorios_pdf_turma;{tid_str}"

                        elif sub == "3":
                            comando = "gerar_boletins_pdf"
                        
                        elif sub == "4":
                            comando = "gerar_relatorio_inteligente"
                        
                        elif sub == "5":
                            if not buscar_e_listar(s, dados_cache, 'turmas', 'listar_turmas'):
                                continue
                            tid_str = input("ID da turma (0 para cancelar): ")
                            if tid_str == "0": continue
                            if not obter_item_cacheado(dados_cache, 'turmas', tid_str):
                                imprimir_resposta("❌ ERRO: ID inválido.")
                                continue
                            comando = f"melhor_pior_aluno_turma;{tid_str}"

                        elif sub == "0": 
                            break
                        else: 
                            print("Inválido.")
                        
                        if comando:
                            resposta = enviar_comando(s, comando)
                            imprimir_resposta(resposta)
                
                # --- Logout ---
                elif op == "5":
                    comando = "logout"
                    resposta = enviar_comando(s, comando)
                    imprimir_resposta(resposta)
                    is_logged_in = False # Seta para False
                    nome_professor_logado = ""
                    print("\nVoltando para a tela de Acesso...")
                    break # Quebra o loop 'while is_logged_in'
                
                # --- Sair ---
                elif op == "0":
                    print("Saindo...")
                    is_logged_in = False # Garante que vai sair do loop mestre
                    break # Quebra o loop 'while is_logged_in'
                
                else:
                    print("Opção inválida.")
                    continue # Volta para o topo do 'while is_logged_in'
            
            # --- FIM DO LOOP 'while is_logged_in' ---
            
            if op == "0": # Se foi por "Sair" (op 0)
                break # Quebra o 'while True:' mestre e encerra o programa
            else: # Se foi por Logout (op 6)
                continue # Volta para o topo do 'while True:', mostrando a tela de login

if __name__ == "__main__":
    main()