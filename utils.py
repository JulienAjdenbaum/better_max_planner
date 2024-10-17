import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///tgvmax.db')

def update_db(engine, new_data_df):
    # Assuming new_data_df is a DataFrame containing the latest API data
    new_data_df.rename(columns={"Disponibilité de places MAX JEUNE et MAX SENIOR":"DISPO"}, inplace=True)
    new_data_df.to_sql('TGVMAX', con=engine, index=False, if_exists='replace')

def run_query(query, params=None, engine=engine, as_list=False):
    with engine.connect() as connection:
        result = connection.execute(text(query), params or {})
        if as_list:
            return [row[0] for row in result.fetchall()]
        return pd.DataFrame(result.fetchall(), columns=result.keys())

def get_all_towns():
    """Return all distinct towns available in the dataset."""
    query = """
        SELECT DISTINCT Origine AS Town FROM TGVMAX
        UNION
        SELECT DISTINCT Destination AS Town FROM TGVMAX;
    """

    return run_query(query, as_list=True)

def find_optimal_trips(station, dates):
    """Return all distinct towns available in the dataset."""
    n_jours = (dates[1]-dates[0]).days
    print(n_jours)
    query = """
    SELECT aller.Destination, aller.Heure_depart, aller.Heure_arrivee, retour.Heure_depart as retour_heure_depart, retour.Heure_arrivee as retour_heure_arrivee, (24*:n_jours - aller.Heure_arrivee + retour.Heure_depart) as temps_sur_place
    FROM TGVMAX as aller
    JOIN (SELECT *
          FROM TGVMAX 
          WHERE DATE = :date2 AND Destination = :ville AND DISPO = 'OUI' AND Axe != 'IC NUIT') as retour
    ON aller.Destination = retour.Origine
    WHERE aller.DATE = :date1 AND aller.DISPO = 'OUI' AND aller.Origine = :ville AND aller.Axe != 'IC NUIT'
    ORDER BY (24 - aller.Heure_arrivee + retour.Heure_depart) DESC
    """
    params = {
        "date1": dates[0],
        "date2": dates[1],
        "ville": station,
        'n_jours':n_jours
    }

    return run_query(query, params=params)



if __name__=="__main__":
    # engine = create_engine('sqlite:///:memory:')
    print(get_all_towns())
    # print(find_optimal_trips("",))


