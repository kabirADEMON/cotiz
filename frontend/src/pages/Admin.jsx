import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import { Alerte, Chargement, EnTete, Personne } from "../components/ui";
import { dateCourte } from "../format";
import { useFetch } from "../useFetch";

function Interrupteur({ actif, onChange, disabled, libelle }) {
  return (
    <button
      role="switch"
      aria-checked={actif}
      aria-label={libelle}
      className={`interrupteur ${actif ? "actif" : ""}`}
      onClick={onChange}
      disabled={disabled}
    >
      <span />
    </button>
  );
}

export default function Admin() {
  const { user: moi } = useAuth();
  const { data: users, erreur: erreurChargement, recharger } = useFetch("/users");
  const [erreur, setErreur] = useState(null);

  if (!users && !erreurChargement) return <Chargement />;

  async function basculer(user, champ) {
    try {
      await api.patch(`/users/${user.id}`, { [champ]: !user[champ] });
      setErreur(null);
      recharger();
    } catch (e) {
      setErreur(e.message);
    }
  }

  return (
    <>
      <EnTete titre="Administration" sousTitre={users ? `${users.length} comptes sur la plateforme` : null} />
      <Alerte message={erreurChargement || erreur} />
      {users && (
        <section className="carte">
          <div className="tableau">
            <table>
              <thead>
                <tr>
                  <th>Utilisateur</th>
                  <th>Email</th>
                  <th>Inscrit le</th>
                  <th>Administrateur</th>
                  <th>Actif</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className={u.is_active ? "" : "ligne-inactive"}>
                    <td><Personne user={u} detail={u.telephone} /></td>
                    <td className="texte-secondaire">{u.email ?? "—"}</td>
                    <td className="texte-secondaire nowrap">{dateCourte(u.created_at)}</td>
                    <td>
                      <Interrupteur actif={u.is_admin} disabled={u.id === moi.id} libelle="Administrateur"
                        onChange={() => basculer(u, "is_admin")} />
                    </td>
                    <td>
                      <Interrupteur actif={u.is_active} disabled={u.id === moi.id} libelle="Compte actif"
                        onChange={() => basculer(u, "is_active")} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
