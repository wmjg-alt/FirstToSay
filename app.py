from website import create_app

#https://www.youtube.com/watch?v=tMNJtYDSOBY

if __name__ == "__main__":
    print('building website...')
    app = create_app()

    app.run(debug=True)