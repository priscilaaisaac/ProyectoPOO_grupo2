from src import create_app

app = create_app()

if __name__ == '__main__':
    print("Iniciando aplicación Flask en http://localhost:5000...")
    app.run(debug=True, port=5000)
