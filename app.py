from website import create_app
app = create_app()

if __name__ == "__main__":
    print('building website...')
    app.run(debug=False, host="0.0.0.0")