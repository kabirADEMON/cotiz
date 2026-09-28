import { Link } from "react-router-dom";
import { Alerte, Badge, Chargement, EnTete, Stat, Vide } from "../components/ui";
import { dateHeure, fcfa } from "../format";
import { useFetch } from "../useFetch";

export default function MesPaiements() {
  const { data: paiements, erreur } = useFetch("/paiements/me");

  if (!paiements && !erreur) return <Chargement />;

  const reussis = paiements?.filter((p) => p.statut === "reussi") ?? [];
  const total = reussis.reduce((s, p) => s + p.montant, 0);
  const mobile = reussis.filter((p) => p.methode === "fedapay").length;

  return (
    <>
      <EnTete titre="Mes paiements" sousTitre="Historique de toutes vos cotisations." />
      <Alerte message={erreur} />

      <div className="stats">
        <Stat icone="wallet" libelle="Total cotisé" valeur={fcfa(total)} />
        <Stat icone="check" libelle="Paiements réussis" valeur={reussis.length} />
        <Stat icone="phone" libelle="Par Mobile Money" valeur={mobile} detail={`${reussis.length - mobile} en espèces`} />
      </div>

      <section className="carte">
        {paiements?.length === 0 ? (
          <Vide icone="wallet" titre="Aucun paiement">Vos cotisations apparaîtront ici.</Vide>
        ) : (
          <div className="tableau">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Tontine</th>
                  <th>Tour</th>
                  <th className="col-montant">Montant</th>
                  <th>Moyen</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {paiements?.map((p) => (
                  <tr key={p.id}>
                    <td className="nowrap texte-secondaire">{dateHeure(p.paye_le ?? p.created_at)}</td>
                    <td><Link to={`/tontines/${p.tontine_id}`} className="lien-fort">{p.tontine_nom}</Link></td>
                    <td><Link to={`/cycles/${p.cycle_id}`}>n°{p.cycle_numero}</Link></td>
                    <td className="col-montant">{fcfa(p.montant)}</td>
                    <td><Badge valeur={p.methode} /></td>
                    <td><Badge valeur={p.statut} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
