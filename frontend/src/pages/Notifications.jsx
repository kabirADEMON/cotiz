import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Icon from "../components/Icon";
import { Alerte, Chargement, EnTete, Vide } from "../components/ui";
import { dateHeure } from "../format";
import { useFetch } from "../useFetch";

const TYPES = {
  rappel_cotisation: { icone: "clock", classe: "notif-rappel" },
  paiement_recu: { icone: "check", classe: "notif-paiement" },
  cagnotte_versee: { icone: "coins", classe: "notif-cagnotte" },
};

export default function Notifications() {
  const navigate = useNavigate();
  const { data: notifications, erreur, recharger } = useFetch("/notifications");

  if (!notifications && !erreur) return <Chargement />;

  async function ouvrir(n) {
    if (!n.lu) await api.post(`/notifications/${n.id}/lu`);
    if (n.cycle_id) navigate(`/cycles/${n.cycle_id}`);
    else recharger();
  }

  async function toutLire() {
    await api.post("/notifications/tout-lu");
    recharger();
  }

  const nonLues = notifications?.filter((n) => !n.lu).length ?? 0;

  return (
    <>
      <EnTete
        titre="Notifications"
        sousTitre={nonLues ? `${nonLues} non lue${nonLues > 1 ? "s" : ""}` : "Vous êtes à jour."}
      >
        {nonLues > 0 && (
          <button className="bouton bouton-secondaire" onClick={toutLire}>Tout marquer comme lu</button>
        )}
      </EnTete>
      <Alerte message={erreur} />

      <section className="carte carte-liste">
        {notifications?.length === 0 ? (
          <Vide icone="bell" titre="Aucune notification" />
        ) : (
          <ul className="notifications">
            {notifications?.map((n) => (
              <li key={n.id}>
                <button className={`notification ${n.lu ? "" : "non-lue"}`} onClick={() => ouvrir(n)}>
                  <span className={`notification-icone ${TYPES[n.type].classe}`}>
                    <Icon name={TYPES[n.type].icone} size={18} />
                  </span>
                  <span className="notification-corps">
                    <span className="notification-message">{n.message}</span>
                    <span className="notification-date">{dateHeure(n.created_at)}</span>
                  </span>
                  {!n.lu && <span className="notification-point" aria-label="Non lue" />}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
