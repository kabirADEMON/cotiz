import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import Icon from "../components/Icon";
import { Alerte, Badge, Chargement, EnTete, Personne, Progression, Stat } from "../components/ui";
import { LIBELLES, PERIODE, dateCourte, fcfa } from "../format";
import { useFetch } from "../useFetch";

function Membres({ tontine, gestion, onChange, setErreur }) {
  const [telephone, setTelephone] = useState("+229");
  const membres = tontine.membres;

  async function action(fn) {
    try {
      await fn();
      setErreur(null);
      onChange();
    } catch (e) {
      setErreur(e.message);
    }
  }

  function deplacer(index, sens) {
    const ids = membres.map((m) => m.id);
    [ids[index], ids[index + sens]] = [ids[index + sens], ids[index]];
    action(() => api.put(`/tontines/${tontine.id}/ordre`, { membre_ids: ids }));
  }

  function ajouter(e) {
    e.preventDefault();
    action(async () => {
      await api.post(`/tontines/${tontine.id}/membres`, { telephone: telephone.replace(/\s/g, "") });
      setTelephone("+229");
    });
  }

  return (
    <section className="carte">
      <div className="carte-entete">
        <div>
          <h2>Membres</h2>
          <p className="carte-sous-titre">
            {gestion ? "L'ordre ci-dessous détermine qui reçoit la cagnotte à chaque tour." : "Ordre de passage"}
          </p>
        </div>
      </div>
      {gestion && (
        <form className="ajout-membre" onSubmit={ajouter}>
          <input
            type="tel"
            value={telephone}
            onChange={(e) => setTelephone(e.target.value)}
            placeholder="Numéro de téléphone du membre"
            aria-label="Numéro de téléphone du membre"
          />
          <button className="bouton bouton-secondaire"><Icon name="plus" /> Ajouter</button>
        </form>
      )}
      <div className="tableau">
        <table>
          <thead>
            <tr>
              <th className="col-tour">Tour</th>
              <th>Membre</th>
              <th>Rôle</th>
              {gestion && <th className="col-actions"><span className="sr-only">Actions</span></th>}
            </tr>
          </thead>
          <tbody>
            {membres.map((m, i) => (
              <tr key={m.id}>
                <td className="col-tour"><span className="pastille-tour">{m.ordre_passage}</span></td>
                <td><Personne user={m.user} detail={m.user.telephone} /></td>
                <td><Badge valeur={m.role} /></td>
                {gestion && (
                  <td className="col-actions">
                    <div className="actions-ligne">
                      <button className="bouton-icone" disabled={i === 0} onClick={() => deplacer(i, -1)} aria-label="Monter">
                        <Icon name="chevronUp" />
                      </button>
                      <button className="bouton-icone" disabled={i === membres.length - 1} onClick={() => deplacer(i, 1)} aria-label="Descendre">
                        <Icon name="chevronDown" />
                      </button>
                      <button
                        className="bouton-icone bouton-icone-danger"
                        aria-label="Retirer"
                        onClick={() => action(() => api.delete(`/tontines/${tontine.id}/membres/${m.id}`))}
                      >
                        <Icon name="x" />
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Calendrier({ cycles }) {
  const navigate = useNavigate();
  const courant = cycles.find((c) => c.statut === "ouvert");

  return (
    <section className="carte">
      <div className="carte-entete">
        <div>
          <h2>Calendrier des tours</h2>
          <p className="carte-sous-titre">Un tour par membre. Le tour en cours est surligné.</p>
        </div>
      </div>
      <div className="tableau">
        <table>
          <thead>
            <tr>
              <th className="col-tour">Tour</th>
              <th>Échéance</th>
              <th>Bénéficiaire</th>
              <th>Collecte</th>
              <th>Statut</th>
              <th className="col-actions"><span className="sr-only">Détails</span></th>
            </tr>
          </thead>
          <tbody>
            {cycles.map((c) => (
              <tr
                key={c.id}
                className={`ligne-cliquable ${c.id === courant?.id ? "ligne-courante" : ""}`}
                onClick={() => navigate(`/cycles/${c.id}`)}
              >
                <td className="col-tour"><span className="pastille-tour">{c.numero}</span></td>
                <td className="nowrap">{dateCourte(c.date_echeance)}</td>
                <td><Personne user={c.beneficiaire.user} /></td>
                <td className="col-collecte">
                  <Progression valeur={c.montant_collecte} max={c.montant_attendu} />
                  <span className="texte-secondaire">{fcfa(c.montant_collecte)} sur {fcfa(c.montant_attendu)}</span>
                </td>
                <td><Badge valeur={c.statut} /></td>
                <td className="col-actions">
                  <Link to={`/cycles/${c.id}`} className="bouton-icone" aria-label={`Voir le tour ${c.numero}`}>
                    <Icon name="chevronRight" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function TontinePage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data: tontine, erreur: erreurChargement, recharger } = useFetch(`/tontines/${id}`);
  const { data: cycles, recharger: rechargerCycles } = useFetch(`/tontines/${id}/cycles`);
  const [erreur, setErreur] = useState(null);

  if (erreurChargement) return <Alerte message={erreurChargement} />;
  if (!tontine) return <Chargement />;

  const estTresorier = tontine.mon_role === "tresorier" || user.is_admin;
  const brouillon = tontine.statut === "brouillon";
  const cagnotte = tontine.montant_cotisation * tontine.membres.length;
  const verses = cycles?.filter((c) => c.statut === "clos").length ?? 0;

  async function demarrer() {
    if (!confirm("Démarrer la tontine ? Les membres et l'ordre de passage ne pourront plus être modifiés.")) return;
    try {
      await api.post(`/tontines/${id}/demarrer`);
      setErreur(null);
      recharger();
      rechargerCycles();
    } catch (e) {
      setErreur(e.message);
    }
  }

  return (
    <>
      <Link to="/" className="fil-ariane"><Icon name="arrowLeft" size={16} /> Tableau de bord</Link>
      <EnTete
        titre={<>{tontine.nom} <Badge valeur={tontine.statut} /></>}
        sousTitre={`${LIBELLES[tontine.frequence]} · 1re échéance le ${dateCourte(tontine.date_debut)}`}
      >
        {estTresorier && brouillon && (
          <button className="bouton" onClick={demarrer}>Démarrer la tontine</button>
        )}
      </EnTete>
      <Alerte message={erreur} />

      <div className="stats">
        <Stat icone="banknote" libelle="Cotisation" valeur={fcfa(tontine.montant_cotisation)} detail={`par ${PERIODE[tontine.frequence]}`} />
        <Stat icone="coins" libelle="Cagnotte par tour" valeur={fcfa(cagnotte)} detail={`${tontine.membres.length} membres`} />
        <Stat
          icone="trending"
          libelle="Avancement"
          valeur={brouillon ? "Non démarrée" : `${verses} / ${tontine.membres.length} tours`}
          detail={brouillon ? "En préparation" : "cagnottes versées"}
        />
      </div>

      {brouillon && (
        <Alerte
          type="info"
          message="Tontine en préparation. Ajoutez les membres (ils doivent avoir un compte), fixez l'ordre de passage, puis démarrez la tontine."
        />
      )}
      {!brouillon && cycles && <Calendrier cycles={cycles} />}
      <Membres tontine={tontine} gestion={estTresorier && brouillon} onChange={recharger} setErreur={setErreur} />
    </>
  );
}
