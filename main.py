 from app import create_app

print(">> Iniciando o sistema SGP...")

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)

