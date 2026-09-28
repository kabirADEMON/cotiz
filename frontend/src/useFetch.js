import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

/** Charge `path` au montage ; `recharger()` relance la requête après une action. */
export function useFetch(path) {
  const [data, setData] = useState(null);
  const [erreur, setErreur] = useState(null);

  const recharger = useCallback(async () => {
    try {
      setData(await api.get(path));
      setErreur(null);
    } catch (e) {
      setErreur(e.message);
    }
  }, [path]);

  useEffect(() => {
    recharger();
  }, [recharger]);

  return { data, erreur, recharger };
}
