import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import Icon from "../components/Icon";
import { Alerte, Badge, Chargement, EnTete, Personne, Progression } from "../components/ui";
import { dateCourte, dateHeure, fcfa, nomComplet } from "../format";
import { useFetch } from "../useFetch";

export default function CyclePage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data: cycle, erreur: erreurChargement, recharger } = useFetch(`/cycles/${id}`);
  const [erreur, setErreur] = useState(null);
  const [enCours, setEnCours] = useState(false);

  if (erreurChargement) return <Alerte message={erreurChargement} />;
  if (!cycle) return <Chargement />;

  const estTresorier = cycle.mon_role === "tresorier" || user.is_admin;
  const ouvert = cycle.statut === "ouvert";
  const monEtat = cycle.etats.find((e) => e.membre.user_id === user.id);
  const nbPayes = cycle.etats.filter((e) => e.a_paye).length;
  const tousOntPaye = nbPayes === cycle.etats.length;

  async function action(fn) {
    setEnCours(true);
    try {
      await fn();
      setErreur(null);
      recharger();
    } catch (e) {
      setErreur(e.message);
    } finally {
      setEnCours(false);
    }
  }

  const payerFedapay = () =>
    action(async () => {
      const { payment_url } = await api.post(`/cycles/${id}/paiements/fedapay`);
      window.location.href = payment_url;
    });

  const encaisser = (membreId) =>
    action(() => api.post(`/cycles/${id}/paiements/especes`, { membre_id: membreId }));

  const cloturer = () => {
    if (confirm(`Confirmer le versement de ${fcfa(cycle.montant_collecte)} à ${nomComplet(cycle.beneficiaire.user)} ?`))
      action(() => api.post(`/cycles/${id}/cloturer`));
  };

  return (
    <>
      <Link to={`/tontines/${cycle.tontine.id}`} className="fil-ariane">
        <Icon name="arrowLeft" size={16} /> {cycle.tontine.nom}
      </Link>
      <EnTete
        titre={<>Tour n°{cycle.numero} <Badge valeur={cycle.statut} /></>}
        sousTitre={`Échéance le ${dateCourte(cycle.date_echeance)}`}
      >
        {monEtat && !monEtat.a_paye && ouvert && (
          <button className="bouton" onClick={payerFedapay} disabled={enCours}>
            <Icon name="phone" /> Payer {fcfa(cycle.tontine.montant_cotisation)}
          </button>
        )}
      </EnTete>
      <Alerte message={erreur} />
      {monEtat?.a_paye && ouvert && <Alerte type="succes" message="Votre cotisation pour ce tour est réglée." />}

      <div className="grille-cycle">
        <section className="carte">
          <h2 className="carte-titre-petit">Collecte</h2>
          <div className="collecte-montant">
            {fcfa(cycle.montant_collecte)}
            <span> sur {fcfa(cycle.montant_attendu)}</span>
          </div>
          <Progression valeur={cycle.montant_collecte} max={cycle.montant_attendu} />
          <p className="texte-secondaire">{nbPayes} cotisation{nbPayes > 1 ? "s" : ""} sur {cycle.etats.length}</p>
        </section>
        <section className="carte">
          <h2 className="carte-titre-petit">Bénéficiaire</h2>
          <Personne user={cycle.beneficiaire.user} detail={cycle.beneficiaire.user.telephone} />
          <p className="texte-secondaire beneficiaire-statut">
            {cycle.verse_le ? (
              <><Icon name="check" size={15} /> Cagnotte versée le {dateHeure(cycle.verse_le)}</>
            ) : (
              <><Icon name="clock" size={15} /> Versement après réception de toutes les cotisations</>
            )}
          </p>
        </section>
      </div>

      <section className="carte">
        <div className="carte-entete">
          <div>
            <h2>Cotisations</h2>
            <p className="carte-sous-titre">Suivi des paiements de chaque membre pour ce tour.</p>
          </div>
          {estTresorier && ouvert && (
            <button className="bouton" disabled={!tousOntPaye || enCours} onClick={cloturer}
              title={tousOntPaye ? "" : "Toutes les cotisations doivent être réglées"}>
              <Icon name="coins" /> Verser la cagnotte
            </button>
          )}
        </div>
        <div className="tableau">
          <table>
            <thead>
              <tr>
                <th>Membre</th>
                <th>Statut</th>
                <th>Date</th>
                <th>Moyen</th>
                {estTresorier && ouvert && <th className="col-actions"><span className="sr-only">Actions</span></th>}
              </tr>
            </thead>
            <tbody>
              {cycle.etats.map((e) => (
                <tr key={e.membre.id}>
                  <td><Personne user={e.membre.user} /></td>
                  <td><Badge valeur={e.a_paye ? "reussi" : "en_attente"} /></td>
                  <td className="nowrap texte-secondaire">{dateHeure(e.paye_le)}</td>
                  <td>{e.methode ? <Badge valeur={e.methode} /> : <span className="texte-secondaire">—</span>}</td>
                  {estTresorier && ouvert && (
                    <td className="col-actions">
                      {!e.a_paye && (
                        <button className="bouton bouton-secondaire bouton-petit" disabled={enCours} onClick={() => encaisser(e.membre.id)}>
                          <Icon name="banknote" size={16} /> Encaisser
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
