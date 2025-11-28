🖥️ Servidor (ServidorPim.py)

Ele é o cérebro do sistema.

Guarda todas as informações em arquivos JSON (professores, alunos, turmas, atividades e notas).

Recebe comandos enviados pelo cliente.

Executa o que foi pedido (cadastrar, editar, listar, remover, gerar relatórios).

Envia a resposta de volta para o cliente.

Permite vários clientes ao mesmo tempo (usa threads).

Só deixa fazer ações depois que o usuário faz login.

💻 Cliente (ClientePim.py)

É o programa que o usuário usa.

Se conecta ao servidor pela rede.

Exibe menus para o professor:

Gerenciar alunos

Gerenciar turmas

Gerenciar atividades

Lançar notas

Gerar relatórios

Cada escolha do menu vira um comando que o cliente envia ao servidor.

O servidor responde e o cliente mostra o resultado na tela.

Usa um pequeno cache para guardar listas já buscadas, deixando mais rápido.

📡 Como eles conversam?

Cliente e servidor usam sockets TCP e um protocolo simples:

O cliente envia:

o tamanho da mensagem (10 bytes)

depois a mensagem (ex: listar_alunos)

O servidor lê, executa a ação e devolve:

o tamanho da resposta

a resposta (pode ser texto ou JSON)

O cliente imprime tudo de forma organizada.
