from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client # type: ignore
import os
from uuid import UUID


# Configuración de Supabase
SUPABASE_URL = 'https://yqsbrdtvkuexjnjymkmc.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlxc2JyZHR2a3VleGpuanlta21jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQxMjU4NDEsImV4cCI6MjA0OTcwMTg0MX0.sa_1lqpGTUm1ktQlolNxNggbEAgXklPyHFNBSyTs4g4'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuración de la aplicación Flask
app = Flask(__name__)
app.secret_key = 'jhgrgfh*-+jgdfuye4546484d*-+fjgtgdjagdkfh'

# Expiración automática de sesión (12 horas)
SESSION_LIFETIME_HOURS = 12
app.permanent_session_lifetime = timedelta(hours=SESSION_LIFETIME_HOURS)

app.config['DEBUG'] = False  # Deshabilitar el modo depuración
app.config['ENV'] = 'production'

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    nombre_usuario = request.form['nombre_usuario']
    contrasena = request.form['contrasena']
    
    # Validar usuario
    response = supabase.table('usuarios').select('*').eq('nombre_usuario', nombre_usuario).execute()
    user = response.data[0] if response.data else None

    if user and check_password_hash(user['contraseña'], contrasena):
        session['logged_in'] = True
        session['nombre_usuario'] = user['nombre_usuario']
        session['rol'] = user['rol']

        if user['rol'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user['rol'] == 'root':
            return redirect(url_for('root_dashboard'))
    
    flash('Usuario o contraseña incorrectos', 'danger')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Se ha cerrado la sesión exitosamente', 'success')
    return redirect(url_for('index'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'logged_in' in session and session['rol'] == 'admin':
        return render_template('layout_admin.html', nombre_usuario=session['nombre_usuario'])
    return redirect(url_for('index'))

@app.route('/root_dashboard')
def root_dashboard():
    if 'logged_in' in session and session['rol'] == 'root':
        return render_template('layout_root.html', nombre_usuario=session['nombre_usuario'])
    return redirect(url_for('index'))

# Crear usuarios admin (solo root puede hacerlo)
@app.route('/create_admin', methods=['POST'])
def create_admin():
    if 'logged_in' in session and session['rol'] == 'root':
        nombre_usuario = request.form['nombre_usuario']
        contrasena = generate_password_hash(request.form['contrasena'])
        
        supabase.table('usuarios').insert({
            "nombre_usuario": nombre_usuario,
            "contraseña": contrasena,
            "rol": "admin"
        }).execute()

        flash(f'Usuario admin {nombre_usuario} creado exitosamente', 'success')
        return redirect(url_for('root_dashboard'))
    return redirect(url_for('index'))

@app.route('/crear_compromiso', methods=['GET', 'POST'])
def crear_compromiso():
    if 'logged_in' in session and session['rol'] in ['admin', 'root']:
        if request.method == 'POST':
            # Lógica para manejar datos del formulario
            cliente = request.form['cliente']
            cedula = request.form['cedula']
            valor = request.form['valor']
            fecha_compromiso = request.form['fecha_compromiso']
            
            # Validar fecha de compromiso
            fecha_actual = datetime.now()
            fecha_limite = fecha_actual + timedelta(days=31)
            if datetime.strptime(fecha_compromiso, '%Y-%m-%d') <= fecha_limite:
                supabase.table('compromisos').insert({
                "cliente": cliente,
                "cedula": cedula,
                "valor": valor,
                "fecha_compromiso": fecha_compromiso,
                "creado_por": session['nombre_usuario']  # Almacenar el nombre del usuario que creó el compromiso
                }).execute()
                flash('Compromiso creado exitosamente', 'success')
            else:
                flash('La fecha del compromiso debe ser dentro de los próximos 31 días', 'danger')
            return redirect(url_for('admin_dashboard') if session['rol'] == 'admin' else url_for('root_dashboard'))
        
        # Renderizar el formulario para GET
        return render_template('create_commitment.html')
    return redirect(url_for('index'))


# Listar compromisos
@app.route('/list_payment_commitments')
def list_payment_commitments():
    if 'logged_in' in session and session['rol'] in ['admin', 'root']:
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        compromisos = supabase.table('compromisos').select('*').order('fecha_compromiso', desc=True).execute().data
        return render_template('list_commitments.html', compromisos=compromisos)
    return redirect(url_for('index'))



@app.route('/update_payment_commitment/<uuid:id>', methods=['GET', 'POST'])
def update_payment_commitment(id):
    # Aquí, id será un UUID
    try:
        compromiso = supabase.table('compromisos').select('*').eq('id', str(id)).execute().data[0]
    except IndexError:
        # Manejar el caso en que no se encuentre el compromiso con ese ID
        return "Compromiso no encontrado", 404

    if request.method == 'POST':
        nueva_fecha = request.form['fecha_compromiso']
        supabase.table('compromisos').update({
            'fecha_compromiso': nueva_fecha
        }).eq('id', str(id)).execute()
        flash('Fecha de compromiso actualizada exitosamente', 'success')
        return redirect(url_for('list_payment_commitments'))

    return render_template('update_commitment.html', compromiso=compromiso)

@app.route('/create_client', methods=['GET', 'POST'])
def create_client():
    if request.method == 'POST':
        cliente = request.form['cliente']
        cedula = request.form['cedula']
        moto = request.form['moto']
        placa = request.form['placa']        
        

        # Inserción en Supabase
        nuevo_cliente = {
            'cliente': cliente,
            'cedula': cedula,
            'moto': moto,
            'placa': placa,
            
        }

        try:
            supabase.table('clientes').insert(nuevo_cliente).execute()
            flash('Cliente creado exitosamente', 'success')
        except Exception as e:
            flash(f'Error al crear cliente: {e}', 'danger')

        return redirect(url_for('list_clients'))

    return render_template('create_client.html')

# Ruta: Listar Clientes
@app.route('/list_clients')
def list_clients():
    try:
        response = supabase.table('clientes').select('*').order('id').execute()
        clientes = response.data
    except Exception as e:
        flash(f'Error al obtener la lista de clientes: {e}', 'danger')
        clientes = []

    return render_template('list_clients.html', clientes=clientes)

# Ruta: Buscar Cliente
@app.route('/search_client', methods=['GET'])
def search_client():
    query = request.args.get('query', '').strip()  # Obtener la consulta del formulario

    # Verifica que haya un término de búsqueda
    if not query:
        flash('Por favor, ingrese un término para buscar.', 'warning')
        return render_template('search_client.html', query=query, resultados=None)

    try:
        # Realiza la búsqueda en la tabla `clientes` en Supabase
        resultados = supabase.table('clientes').select('*').ilike('placa', f'%{query}%').execute().data
        
        # También busca por cédula, moto o placa
        if not resultados:
            resultados = supabase.table('clientes').select('*').or_(
                f"placa.ilike('%{query}%,cliente.ilike('%{query}%')"
            ).execute().data

    except Exception as e:
        flash(f'Error al buscar cliente: {e}', 'danger')
        resultados = []

    # Renderiza el template con los resultados
    return render_template('search_client.html', query=query, resultados=resultados)






if __name__ == '__main__':
    app.run(debug=True)
