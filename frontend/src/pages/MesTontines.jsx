import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import Icon from "../components/Icon";
import { Alerte, Badge, Chargement, EnTete, Modale, Stat, Vide } from "../components/ui";
import { PERIODE, dateCourte, fcfa } from "../format";
import { useFetch } from "../useFetch";

function NouvelleTontine({ onFermer }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    nom: "",
    montant_cotisation: 5000,
    frequence: "mensuelle",
    date_debut: new Date().toISOString().slice(0, 10),
  });
  const [erreur, setErreur] = useState(null);
  const champ = (nom) => ({ value: form[nom], onChange: (e) => setForm({ ...form, [nom]: e.target.value }) });

  async function soumettre(e) {
    e.preventDefault();
    try {
      const tontine = await api.post("/tontines", { ...form, montant_cotisation: Number(form.montant_cotisation) });
      navigate(`/tontines/${tontine.id}`);
    } catch (err) {
      setErreur(err.message);
    }
  }

  return (
    <Modale titre="Nouvelle tontine" onFermer={onFermer}>
      <form onSubmit={soumettre}>
        <Alerte message={erreur} />
        <label className="champ">
          <span>Nom de la tontine</span>
          <input {...champ("nom")} placeholder="Tontine du quartier" autoFocus required />
        </label>
        <div className="grille-champs">
          <label className="champ">
            <span>Cotisation (FCFA)</span>
            <input type="number" min={1} step={100} {...champ("montant_cotisation")} required />
          </label>
          <label className="champ">
            <span>Fréquence</span>
            <select {...champ("frequence")}>
              <option value="quotidienne">Quotidienne</option>
              <option value="hebdomadaire">Hebdomadaire</option>
              <option value="mensuelle">Mensuelle</option>
            </select>
          </label>
        </div>
        <label className="champ">
          <span>Première échéance</span>
          <input type="date" {...champ("date_debut")} required />
        </label>
        <p className="note">
          Vous serez trésorier de la tontine. Vous pourrez ensuite inviter les membres et fixer l'ordre de passage.
        </p>
        <div className="modale-actions">
          <button type="button" className="bouton bouton-secondaire" onClick={onFermer}>Annuler</button>
          <button className="bouton">Créer la tontine</button>
        </div>
      </form>
    </Modale>
  );
}

function CarteTontine({ tontine: t }) {
  return (
    <Link to={`/tontines/${t.id}`} className="carte carte-tontine">
      <div className="carte-tontine-haut">
        <h3>{t.nom}</h3>
        <Badge valeur={t.statut} />
      </div>
      <div className="carte-tontine-montant">
        {fcfa(t.montant_cotisation)}
        <span> / {PERIODE[t.frequence]}</span>
      </div>
      <dl className="carte-tontine-infos">
        <div>
          <dt><Icon name="users" size={15} /> Membres</dt>
          <dd>{t.nb_membres}</dd>
        </div>
        <div>
          <dt><Icon name="coins" size={15} /> Cagnotte</dt>
          <dd>{fcfa(t.montant_cotisation * t.nb_membres)}</dd>
        </div>
        <div>
          <dt><Icon name="calendar" size={15} /> {t.statut === "brouillon" ? "Début" : "Échéance"}</dt>
          <dd>{t.statut === "terminee" ? "—" : dateCourte(t.prochaine_echeance ?? t.date_debut)}</dd>
        </div>
      </dl>
    </Link>
  );
}

export default function MesTontines() {
  const { user } = useAuth();
  const { data: tontines, erreur } = useFetch("/tontines");
  const { data: paiements } = useFetch("/paiements/me");
  const [creation, setCreation] = useState(false);

  if (!tontines && !erreur) return <Chargement />;

  const actives = tontines?.filter((t) => t.statut === "active") ?? [];
  const totalCotise = paiements?.filter((p) => p.statut === "reussi").reduce((s, p) => s + p.montant, 0) ?? 0;
  const prochaine = actives
    .filter((t) => t.prochaine_echeance)
    .sort((a, b) => a.prochaine_echeance.localeCompare(b.prochaine_echeance))[0];

  return (
    <>
      <EnTete titre={`Bonjour, ${user.prenom}`} sousTitre="Voici l'état de vos tontines.">
        <button className="bouton" onClick={() => setCreation(true)}>
          <Icon name="plus" /> Nouvelle tontine
        </button>
      </EnTete>
      <Alerte message={erreur} />

      <div className="stats">
        <Stat icone="trending" libelle="Tontines en cours" valeur={actives.length} detail={`${tontines?.length ?? 0} au total`} />
        <Stat icone="wallet" libelle="Total cotisé" valeur={fcfa(totalCotise)} detail={`${paiements?.filter((p) => p.statut === "reussi").length ?? 0} paiements`} />
        <Stat
          icone="calendar"
          libelle="Prochaine échéance"
          valeur={prochaine ? dateCourte(prochaine.prochaine_echeance) : "—"}
          detail={prochaine?.nom}
        />
      </div>

      <h2 className="titre-section">Mes tontines</h2>
      {tontines?.length === 0 ? (
        <div className="carte">
          <Vide icone="users" titre="Aucune tontine pour l'instant">
            Créez votre première tontine, ou demandez à un trésorier de vous ajouter avec votre numéro.
          </Vide>
        </div>
      ) : (
        <div className="grille-tontines">
          {tontines?.map((t) => <CarteTontine key={t.id} tontine={t} />)}
        </div>
      )}

      {creation && <NouvelleTontine onFermer={() => setCreation(false)} />}
    </>
  );
}
