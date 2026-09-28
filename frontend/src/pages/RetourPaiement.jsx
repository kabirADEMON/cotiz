import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import Icon from "../components/Icon";
import { Alerte, Chargement } from "../components/ui";
import { fcfa } from "../format";

const ETATS = {
  reussi: { icone: "check", classe: "succes", titre: "Paiement confirmé", texte: "Merci, votre cotisation a bien été enregistrée." },
  echoue: { icone: "alert", classe: "erreur", titre: "Paiement non abouti", texte: "Aucun montant n'a été prélevé. Vous pouvez réessayer depuis la page du tour." },
  en_attente: { icone: "clock", classe: "attente", titre: "Paiement en cours", texte: "La confirmation peut prendre quelques instants. Actualisez cette page." },
};

export default function RetourPaiement() {
  const { id } = useParams();
  const [paiement, setPaiement] = useState(null);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    api.post(`/paiements/${id}/verifier`).then(setPaiement).catch((e) => setErreur(e.message));
  }, [id]);

  if (erreur) return <Alerte message={erreur} />;
  if (!paiement) return <Chargement />;

  const etat = ETATS[paiement.statut];
  return (
    <div className="carte resultat">
      <div className={`resultat-icone resultat-${etat.classe}`}>
        <Icon name={etat.icone} size={28} />
      </div>
      <h1>{etat.titre}</h1>
      <p className="resultat-montant">{fcfa(paiement.montant)}</p>
      <p className="texte-secondaire">{etat.texte}</p>
      <Link className="bouton" to={`/cycles/${paiement.cycle_id}`}>Retour au tour</Link>
    </div>
  );
}
