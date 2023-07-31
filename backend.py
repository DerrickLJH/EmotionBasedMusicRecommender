import mysql.connector as mariadb
import csv
import codecs

conn_params = {
    'user': 'root',
    'password': 'password',
    'host': 'localhost',
    'database': 'dataengproj'
}


def create_table(conn_params):
    # Create table
    command = \
        """
    CREATE TABLE IF NOT EXISTS songs (
        name VARCHAR(255),
        album VARCHAR(255),
        artist VARCHAR(255),
        id VARCHAR(255),
        release_date VARCHAR(255),
        popularity INT,
        length INT,
        danceability FLOAT,
        acousticness FLOAT,
        energy FLOAT,
        instrumentalness FLOAT, 
        liveness FLOAT,
        valence FLOAT,
        loudness FLOAT,
        speechiness FLOAT,
        tempo FLOAT,
        `key` SMALLINT,
        time_signature SMALLINT,
        mood VARCHAR(255),
        genre VARCHAR(255),
        PRIMARY KEY (id)
    );
    """

    conn = None
    try:
        print('Connecting to the database...')

        # Establish connection
        conn = mariadb.connect(**conn_params)

        # Create cursor
        cur = conn.cursor()

        # Execute commands
        cur.execute(command)

        # Close the communication with the database server
        cur.close()

        # Commit changes
        conn.commit()
        print('Table created successfully.')

    except (Exception, mariadb.Error) as error:
        print(error)

    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


def insert_values(conn_params):
    conn = None
    try:
        print('Connecting to the database...')
        # Establish connection
        conn = mariadb.connect(**conn_params)

        # Create cursor
        cur = conn.cursor()

        with codecs.open(r'data_moods.csv', 'r',
                         encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            next(csv_reader)  # Skip header row

            for row in csv_reader:
                name = row['name']
                album = row['album']
                artist = row['artist']
                id = row['id']
                release_date = row['release_date']
                popularity = row['popularity']
                length = row['length']
                danceability = row['danceability']
                acousticness = row['acousticness']
                energy = row['energy']
                instrumentalness = row['instrumentalness']
                liveness = row['liveness']
                valence = row['valence']
                loudness = row['loudness']
                speechiness = row['speechiness']
                tempo = row['tempo']
                key = row['key']
                time_signature = row['time_signature']
                mood = row['mood']
                genre = row['genre']

                query = 'INSERT INTO songs (name, album, artist, id, release_date, popularity, length, danceability, ' \
                        'acousticness, energy, instrumentalness, liveness, valence, loudness, speechiness, tempo, ' \
                        '`key`, time_signature, mood, genre) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ' \
                        '%s, %s, %s, %s, %s, %s, %s, %s); '

                cur.execute(query, (
                    name, album, artist, id, release_date, popularity, length, danceability, acousticness, energy,
                    instrumentalness, liveness, valence, loudness, speechiness, tempo, key, time_signature, mood,
                    genre))

        # Close the communication with the database server
        cur.close()

        # Commit changes
        conn.commit()
        print('Data inserted successfully into table.')

    except (Exception, mariadb.Error) as error:
        print(error)

    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


def drop_table(conn_params):
    conn = None
    try:
        print('Connecting to the database...')
        # Establish connection
        conn = mariadb.connect(**conn_params)

        # Create cursor
        cur = conn.cursor()

        # Drop table
        table_name = 'songs'  # Replace with the actual table name you want to drop
        drop_query = f'DROP TABLE IF EXISTS {table_name};'
        cur.execute(drop_query)

        # Close the communication with the database server
        cur.close()

        # Commit changes
        conn.commit()
        print(f'Table {table_name} dropped successfully.')

    except (Exception, mariadb.Error) as error:
        print(error)

    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


def get_track_by_mood(mood, conn_params):
    conn = None
    track_info = None
    try:
        print('Connecting to the database...')
        conn = mariadb.connect(**conn_params)
        cur = conn.cursor()
        query = f"SELECT * FROM songs WHERE mood = '{mood}' ORDER BY popularity DESC LIMIT 10"
        cur.execute(query)
        track_info = cur.fetchall()
        cur.close()

        # Commit changes (not necessary for SELECT queries)
        # conn.commit()

    except mariadb.Error as error:
        print(f"Error accessing database: {error}")

    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')
    return track_info


def get_number_of_tables(conn_params):
    conn = None
    num_tables = 0
    try:
        print('Connecting to the database...')
        conn = mariadb.connect(**conn_params)
        cur = conn.cursor()

        # SQL query to get the list of tables
        query = "SHOW TABLES"
        cur.execute(query)

        # Fetch all rows and count the number of tables
        num_tables = len(cur.fetchall())

        cur.close()

    except mariadb.Error as error:
        print(f"Error accessing database: {error}")

    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')
    return num_tables


def create_database(database_name, conn_params):
    conn = None
    try:
        print('Connecting to the database...')
        conn = mariadb.connect(**conn_params)
        cur = conn.cursor()

        # SQL query to create the new database
        create_db_query = f"CREATE DATABASE {database_name};"
        cur.execute(create_db_query)

        cur.close()

    except mariadb.Error as error:
        print(f"Error creating database: {error}")

    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


# Call the function to create a new database with the name "new_database"
# new_database_name = "data_engineering_proj"
# create_database(new_database_name, conn_params)

# Run the code
# create_table(conn_params)
# insert_values(conn_params)
# drop_table(conn_params)

num_tables = get_number_of_tables(conn_params)
print(f"Number of tables in 'dataengproj': {num_tables}")
