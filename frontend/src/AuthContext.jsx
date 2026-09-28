import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [chargement, setChargement] = useState(Boolean(getToken()));

  const chargerProfil = useCallback(async () => {
    try {
      setUser(await api.get("/auth/me"));
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => {
    if (getToken()) chargerProfil();
  }, [chargerProfil]);

  async function connexion(telephone, password) {
    const { access_token } = await api.login(telephone, password);
    setToken(access_token);
    await chargerProfil();
  }

  function deconnexion() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, chargement, connexion, deconnexion }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
