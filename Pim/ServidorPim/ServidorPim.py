import json
import os
import hashlib
import socket
import threading
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

ARQ_PROF = "professores.json"
ARQ_ALUN = "alunos.json"
ARQ_TURM = "turmas.json"
ARQ_ATIV = "atividades.json"

professores = []
alunos = []
turmas = []
atividades = []

dados_lock = threading.Lock()

def carregar_arquivo(nome, default=[]):
    with dados_lock:
        if os.path.exists(nome):
            try:
                with open(nome, "r", encoding="utf-8") as f:
                    conteudo = f.read()
                    if not conteudo:
                        return default
                    return json.loads(conteudo)
            except json.JSONDecodeError:
                print(f"AVISO: Arquivo '{nome}' corrompido ou vazio. Iniciando com dados padrão.")
                return default
            except Exception as e:
                print(f"ERRO ao ler {nome}: {e}")
                return default
        return default

def salvar_arquivo(nome, dados):
    with dados_lock:
        try:
            with open(nome, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"ERRO CRÍTICO ao salvar {nome}: {e}")

def salvar_tudo():
    salvar_arquivo(ARQ_PROF, professores)
    salvar_arquivo(ARQ_ALUN, alunos)
    salvar_arquivo(ARQ_TURM, turmas)
    salvar_arquivo(ARQ_ATIV, atividades)

def carregar_tudo():
    global professores, alunos, turmas, atividades
    print(">> Carregando 'professores.json'...")
    professores = carregar_arquivo(ARQ_PROF, [])
    print(">> Carregando 'alunos.json'...")
    alunos = carregar_arquivo(ARQ_ALUN, [])
    print(">> Carregando 'turmas.json'...")
    turmas = carregar_arquivo(ARQ_TURM, [])
    print(">> Carregando 'atividades.json'...")
    atividades = carregar_arquivo(ARQ_ATIV, [])
    print(">> Verificando e salvando arquivos...")
    salvar_tudo()

def prox_id(lista):
    ids = [int(x.get("id", 0)) for x in lista if str(x.get("id")).isdigit()]
    return max(ids, default=0) + 1

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def buscar_professor_por_id(pid):
    try:
        pid_int = int(pid)
        return next((p for p in professores if p["id"] == pid_int), None)
    except ValueError:
        return None

def buscar_aluno_por_id(aid):
    try:
        aid_int = int(aid)
        return next((a for a in alunos if a["id"] == aid_int), None)
    except ValueError:
        return None

def buscar_turma_por_id(tid):
    try:
        tid_int = int(tid)
        return next((t for t in turmas if t["id"] == tid_int), None)
    except ValueError:
        return None

def buscar_atividade_por_id(aid):
    try:
        aid_int = int(aid)
        return next((a for a in atividades if a["id"] == aid_int), None)
    except ValueError:
        return None

def login_professor(matricula, senha_plana):
    senha_hash = hash_senha(senha_plana)
    for p in professores:
        if p["matricula"] == matricula and p["senha"] == senha_hash:
            print(f"[Log Servidor] Login bem-sucedido para: {p['nome']}")
            return p
    print(f"[Log Servidor] Tentativa de login falhou para matrícula: {matricula}")
    return None

def listar_professores():
    if not professores: return json.dumps([])
    return json.dumps(professores)

def cadastrar_professor(nome, matricula, senha_plana):
    if any(p["matricula"].lower() == matricula.lower() for p in professores):
        return "❌ ERRO: Matrícula já cadastrada."
    pid = prox_id(professores)
    professores.append({"id": pid, "nome": nome, "matricula": matricula, "senha": hash_senha(senha_plana)})
    salvar_arquivo(ARQ_PROF, professores)
    print(f"[Log Servidor] Professor cadastrado: {nome}")
    return "✅ Professor cadastrado."
def editar_professor(pid_str, novo_nome, nova_mat, nova_senha_plana):
    p = buscar_professor_por_id(pid_str)
    if not p: return "❌ ERRO: Professor não encontrado."
    if novo_nome: p["nome"] = novo_nome
    if nova_mat: p["matricula"] = nova_mat
    if nova_senha_plana: p["senha"] = hash_senha(nova_senha_plana)
    salvar_arquivo(ARQ_PROF, professores)
    print(f"[Log Servidor] Professor editado: ID {pid_str}")
    return "✅ Professor atualizado."

def remover_professor(pid_str):
    p = buscar_professor_por_id(pid_str)
    if not p: return "❌ ERRO: Professor não encontrado."
    professores.remove(p)
    salvar_arquivo(ARQ_PROF, professores)
    print(f"[Log Servidor] Professor removido: {p['nome']}")
    return "✅ Professor removido."

def listar_alunos():
    if not alunos: return json.dumps([])
    return json.dumps(alunos)

def cadastrar_aluno(nome, matricula):
    if any(x["matricula"].lower() == matricula.lower() for x in alunos):
        return "❌ ERRO: Matrícula já cadastrada."
    aid = prox_id(alunos)
    alunos.append({"id": aid, "nome": nome, "matricula": matricula})
    salvar_arquivo(ARQ_ALUN, alunos)
    print(f"[Log Servidor] Aluno cadastrado: {nome}")
    return "✅ Aluno cadastrado."

def editar_aluno(aid_str, novo_nome, nova_mat):
    a = buscar_aluno_por_id(aid_str)
    if not a: return "❌ ERRO: Aluno não encontrado."
    if novo_nome: a['nome'] = novo_nome
    if nova_mat: a['matricula'] = nova_mat
    salvar_arquivo(ARQ_ALUN, alunos)
    print(f"[Log Servidor] Aluno editado: ID {aid_str}")
    return "✅ Aluno atualizado."

def remover_aluno(aid_str):
    a = buscar_aluno_por_id(aid_str)
    if not a: return "❌ ERRO: Aluno não encontrado."
    aid = a['id']
    for t in turmas:
        if aid in t.get("alunos", []):
            t["alunos"].remove(aid)
    for atv in atividades:
        if str(aid) in atv.get("notas", {}):
            del atv["notas"][str(aid)]
    alunos.remove(a)
    salvar_tudo()
    print(f"[Log Servidor] Aluno removido: {a['nome']}")
    return "✅ Aluno removido."

def buscar_aluno(query):
    encontrados = [a for a in alunos if query in a["nome"].lower() or query in a["matricula"].lower()]
    return json.dumps(encontrados)

def ver_turmas_do_aluno(aid_str):
    a = buscar_aluno_por_id(aid_str)
    if not a: return "❌ ERRO: Aluno não encontrado."
    aid = a['id']
    turmas_do_aluno = [t for t in turmas if aid in t.get("alunos", [])]
    if not turmas_do_aluno:
        return "Aluno não está matriculado em nenhuma turma."
    turmas_info = [{"id": t["id"], "nome": t["nome"]} for t in turmas_do_aluno]
    return json.dumps(turmas_info)

def listar_turmas():
    if not turmas: return json.dumps([])
    lista = []
    for t in turmas:
        lista.append({
            "id": t.get('id', 0),
            "nome": t.get('nome', 'N/D'),
            "alunos": len(t.get('alunos', [])),
            "atividades": len(t.get('atividades', []))
        })
    return json.dumps(lista)

def cadastrar_turma(nome):
    tid = prox_id(turmas)
    turmas.append({"id": tid, "nome": nome, "alunos": [], "atividades": []})
    salvar_arquivo(ARQ_TURM, turmas)
    print(f"[Log Servidor] Turma cadastrada: {nome}")
    return "✅ Turma cadastrada."

def editar_turma(tid_str, novo_nome):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    if novo_nome: t['nome'] = novo_nome
    salvar_arquivo(ARQ_TURM, turmas)
    print(f"[Log Servidor] Turma editada: ID {tid_str}")
    return "✅ Turma atualizada."

def remover_turma(tid_str):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    tid = t['id']
    atv_to_remove = [a for a in atividades if a.get("turma_id") == tid]
    for a in atv_to_remove:
        atividades.remove(a)
    turmas.remove(t)
    salvar_tudo()
    print(f"[Log Servidor] Turma removida: {t['nome']}")
    return "✅ Turma e atividades associadas removidas."
def ver_alunos_da_turma(tid_str):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    if not t.get("alunos"): return "Nenhum aluno matriculado nesta turma."
    lista_alunos_turma = []
    for aid in t["alunos"]:
        a = buscar_aluno_por_id(aid)
        if a:
            lista_alunos_turma.append({"id": a['id'], "matricula": a['matricula'], "nome": a['nome']})
    return json.dumps(lista_alunos_turma)

def ver_atividades_da_turma(tid_str):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    if not t.get("atividades"): return "Nenhuma atividade nesta turma."
    lista_atv_turma = []
    for aid in t["atividades"]:
        atv = buscar_atividade_por_id(aid)
        if atv:
            lista_atv_turma.append({"id": atv['id'], "nome": atv['nome'], "descricao": atv.get("descricao", "")})
    return json.dumps(lista_atv_turma)

def matricular_aluno_em_turma(aid_str, tid_str):
    a = buscar_aluno_por_id(aid_str)
    t = buscar_turma_por_id(tid_str)
    if not a: return "❌ ERRO: Aluno não encontrado."
    if not t: return "❌ ERRO: Turma não encontrada."
    aid = a['id']
    if aid in t.get("alunos", []): return "Aluno já matriculado."
    t["alunos"].append(aid)
    salvar_arquivo(ARQ_TURM, turmas)
    print(f"[Log Servidor] Aluno {a['nome']} matriculado na {t['nome']}")
    return "✅ Matriculado com sucesso."

def desmatricular_aluno(tid_str, aid_str):
    t = buscar_turma_por_id(tid_str)
    a = buscar_aluno_por_id(aid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    if not a: return "❌ ERRO: Aluno não encontrado."
    aid = a['id']
    if aid not in t.get("alunos", []): return "❌ ERRO: Aluno não está matriculado nessa turma."
    t["alunos"].remove(aid)
    for atv_id in list(t.get("atividades", [])):
        atv = buscar_atividade_por_id(atv_id)
        if atv and str(aid) in atv.get("notas", {}):
            del atv["notas"][str(aid)]
    salvar_tudo()
    print(f"[Log Servidor] Aluno ID {aid} desmatriculado da {t['nome']}")
    return "✅ Desmatriculado."

def listar_atividades():
    if not atividades: return json.dumps([])
    lista = []
    for a in atividades:
        t = buscar_turma_por_id(a.get("turma_id"))
        lista.append({
            "id": a.get('id', 0),
            "nome": a.get('nome', 'N/D'),
            "turma_nome": t["nome"] if t else "N/D",
            "descricao": a.get("descricao", "")
        })
    return json.dumps(lista)

def cadastrar_atividade(tid_str, nome, descricao):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    aid = prox_id(atividades)
    atv = {"id": aid, "nome": nome, "descricao": descricao, "turma_id": t['id'], "notas": {}}
    atividades.append(atv)
    t.setdefault("atividades", []).append(aid)
    salvar_tudo()
    print(f"[Log Servidor] Atividade '{nome}' cadastrada na {t['nome']}")
    return "✅ Atividade cadastrada."

def editar_atividade(aid_str, novo_nome, nova_descr):
    atv = buscar_atividade_por_id(aid_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    if novo_nome: atv["nome"] = novo_nome
    if nova_descr: atv["descricao"] = nova_descr
    salvar_arquivo(ARQ_ATIV, atividades)
    print(f"[Log Servidor] Atividade editada: ID {aid_str}")
    return "✅ Atividade atualizada."

def remover_atividade(aid_str):
    atv = buscar_atividade_por_id(aid_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    tid = atv.get("turma_id")
    if tid:
        t = buscar_turma_por_id(tid)
        if t and atv['id'] in t.get("atividades", []):
            t["atividades"].remove(atv['id'])
    atividades.remove(atv)
    salvar_tudo()
    print(f"[Log Servidor] Atividade removida: {atv['nome']}")
    return "✅ Atividade removida."

def ver_notas_atividade(aid_str):
    atv = buscar_atividade_por_id(aid_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    if not atv.get("notas"): return "Sem notas registradas."
    lista_notas = []
    for sid, nota in atv["notas"].items():
        aluno = buscar_aluno_por_id(sid)
        lista_notas.append({
            "id_aluno": sid,
            "nome": aluno["nome"] if aluno else "Aluno Removido",
            "nota": nota
        })
    return json.dumps(lista_notas)

def adicionar_editar_nota(atv_id_str, aluno_id_str, nota_str):
    atv = buscar_atividade_por_id(atv_id_str)
    aluno = buscar_aluno_por_id(aluno_id_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    if not aluno: return "❌ ERRO: Aluno não encontrado."
    try:
        nota = float(nota_str.replace(",", "."))
        if not (0.0 <= nota <= 10.0): return "❌ ERRO: Nota deve ser entre 0 e 10."
    except ValueError:
        return "❌ ERRO: Nota deve ser um número."
    t = buscar_turma_por_id(atv.get("turma_id"))
    if not t: return "❌ ERRO: Turma da atividade não encontrada."
    if aluno['id'] not in t.get("alunos", []): return "❌ ERRO: Aluno não pertence a esta turma."
    atv.setdefault("notas", {})[str(aluno['id'])] = nota
    salvar_arquivo(ARQ_ATIV, atividades)
    print(f"[Log Servidor] Nota {nota} registrada para Aluno ID {aluno_id_str} em Atividade ID {atv_id_str}")
    return "✅ Nota registrada/atualizada."
def remover_nota(atv_id_str, aluno_id_str):
    atv = buscar_atividade_por_id(atv_id_str)
    if not atv: return "❌ ERRO: Atividade não encontrada."
    aluno = buscar_aluno_por_id(aluno_id_str)
    if not aluno: return "❌ ERRO: Aluno não encontrado."
    sid = str(aluno['id'])
    if sid not in atv.get("notas", {}): return "❌ Este aluno não possui nota cadastrada."
    del atv["notas"][sid]
    salvar_arquivo(ARQ_ATIV, atividades)
    print(f"[Log Servidor] Nota removida de Aluno ID {aluno_id_str} da Atividade ID {atv_id_str}")
    return "Nota removida."

def gerar_relatorio_turma(tid_str, caminho_pdf):
    t = buscar_turma_por_id(tid_str)
    if not t: return "❌ ERRO: Turma não encontrada."
    if not os.path.exists(os.path.dirname(caminho_pdf)):
        try:
            os.makedirs(os.path.dirname(caminho_pdf), exist_ok=True)
        except Exception as e:
            return f"❌ ERRO: Não foi possível criar diretório: {e}"
    c = canvas.Canvas(caminho_pdf, pagesize=letter)
    largura, altura = letter
    y = altura - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Relatório da Turma: {t['nome']}")
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Alunos:")
    y -= 20
    for aid in t.get("alunos", []):
        a = buscar_aluno_por_id(aid)
        if a:
            c.setFont("Helvetica", 11)
            c.drawString(60, y, f"{a['nome']} (Matrícula: {a['matricula']})")
            y -= 15
            if y < 50:
                c.showPage()
                y = altura - 50
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Atividades:")
    y -= 20
    for atv_id in t.get("atividades", []):
        atv = buscar_atividade_por_id(atv_id)
        if atv:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(60, y, f"Atividade: {atv['nome']}")
            y -= 15
            c.setFont("Helvetica", 10)
            for sid, nota in atv.get("notas", {}).items():
                aluno = buscar_aluno_por_id(sid)
                nome_alu = aluno["nome"] if aluno else "Aluno removido"
                c.drawString(80, y, f"{nome_alu}: {nota}")
                y -= 15
                if y < 50:
                    c.showPage()
                    y = altura - 50
            y -= 10
    c.save()
    print(f"[Log Servidor] Relatório PDF gerado em: {caminho_pdf}")
    return "PDF gerado com sucesso."

def processar_comandos(comando_json):
    try:
        cmd = json.loads(comando_json)
    except:
        return "❌ JSON inválido."
    acao = cmd.get("acao")
    if acao == "listar_professores": return listar_professores()
    if acao == "cadastrar_professor": return cadastrar_professor(cmd.get("nome"), cmd.get("matricula"), cmd.get("senha"))
    if acao == "editar_professor": return editar_professor(cmd.get("id"), cmd.get("nome"), cmd.get("matricula"), cmd.get("senha"))
    if acao == "remover_professor": return remover_professor(cmd.get("id"))
    if acao == "listar_alunos": return listar_alunos()
    if acao == "cadastrar_aluno": return cadastrar_aluno(cmd.get("nome"), cmd.get("matricula"))
    if acao == "editar_aluno": return editar_aluno(cmd.get("id"), cmd.get("nome"), cmd.get("matricula"))
    if acao == "remover_aluno": return remover_aluno(cmd.get("id"))
    if acao == "buscar_aluno": return buscar_aluno(cmd.get("query"))
    if acao == "ver_turmas_do_aluno": return ver_turmas_do_aluno(cmd.get("id"))
    if acao == "listar_turmas": return listar_turmas()
    if acao == "cadastrar_turma": return cadastrar_turma(cmd.get("nome"))
    if acao == "editar_turma": return editar_turma(cmd.get("id"), cmd.get("nome"))
    if acao == "remover_turma": return remover_turma(cmd.get("id"))
    if acao == "ver_alunos_da_turma": return ver_alunos_da_turma(cmd.get("id"))
    if acao == "ver_atividades_da_turma": return ver_atividades_da_turma(cmd.get("id"))
    if acao == "matricular_aluno": return matricular_aluno_em_turma(cmd.get("aluno_id"), cmd.get("turma_id"))
    if acao == "desmatricular_aluno": return desmatricular_aluno(cmd.get("turma_id"), cmd.get("aluno_id"))
    if acao == "listar_atividades": return listar_atividades()
    if acao == "cadastrar_atividade": return cadastrar_atividade(cmd.get("turma_id"), cmd.get("nome"), cmd.get("descricao"))
    if acao == "editar_atividade": return editar_atividade(cmd.get("id"), cmd.get("nome"), cmd.get("descricao"))
    if acao == "remover_atividade": return remover_atividade(cmd.get("id"))
    if acao == "ver_notas_atividade": return ver_notas_atividade(cmd.get("id"))
    if acao == "adicionar_nota": return adicionar_editar_nota(cmd.get("atividade_id"), cmd.get("aluno_id"), cmd.get("nota"))
    if acao == "remover_nota": return remover_nota(cmd.get("atividade_id"), cmd.get("aluno_id"))
    return "❌ Ação desconhecida."
def tratar_cliente(conn, addr):
    print(f"[CONEXÃO] Cliente conectado: {addr}")
    conn.sendall("Conexão estabelecida com o servidor Python.\n".encode())
    user_logado = None
    while True:
        try:
            dados = conn.recv(4096)
            if not dados:
                print(f"[CONEXÃO] Cliente desconectado: {addr}")
                break
            mensagem = dados.decode().strip()
            print(f"[RECEBIDO de {addr}]: {mensagem}")
            if mensagem.startswith("LOGIN"):
                try:
                    _, matr, senha = mensagem.split(" ", 2)
                    prof = login_professor(matr, senha)
                    if prof:
                        user_logado = prof
                        resposta = f"LOGIN_OK {prof['nome']}"
                    else:
                        resposta = "LOGIN_FALHOU"
                except:
                    resposta = "ERRO_LOGIN"
                conn.sendall(resposta.encode())
                continue
            if not user_logado:
                conn.sendall("NECESSARIO_LOGIN".encode())
                continue
            resposta = processar_comandos(mensagem)
            conn.sendall(str(resposta).encode())
        except ConnectionResetError:
            print(f"[ERRO] Conexão perdida com {addr}")
            break
        except Exception as e:
            print(f"[ERRO inesperado]: {e}")
            break
    conn.close()

def iniciar_servidor():
    carregar_tudo()
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("0.0.0.0", 5050))
    servidor.listen(5)
    print("Servidor iniciado na porta 5050. Aguardando conexões...")
    while True:
        conn, addr = servidor.accept()
        thread_cliente = threading.Thread(target=tratar_cliente, args=(conn, addr))
        thread_cliente.start()

if __name__ == "__main__":
    iniciar_servidor()
