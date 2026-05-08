# Renda Next-Gen: Architektúra Tervezet (V4.0)

Ez a dokumentum a **"Top Tier"** szoftverarchitektúrát vázolja fel egy modern, Python + PySide alapú asztali alkalmazáshoz. A cél egy olyan rendszer, amely skálázható, könnyen tesztelhető, és teljesen kiküszöböli a UI lefagyásokat és a "race condition"-öket.

---

## 1. Alapelvek: State-Driven Design

A hagyományos architektúra (ahol a UI közvetlenül hívja az adatbázist) helyett egy **reaktív, állapotalapú** modellt használunk.

### A Single Source of Truth (SSOT)
Minden adat egyetlen központi helyen, az **AppState**-ben (Store) él a memóriában. A UI soha nem kérdezheti le közvetlenül az adatbázist vagy az API-t; minden információt a Store-ból kap.

### Unidirectional Data Flow (UDF)
Az adatok csak egy irányba mozognak:
1.  **User Action**: A felhasználó kattint egyet (pl. "Scan").
2.  **Controller (Async)**: Lefut a háttérben a logika (API hívás, fájlrendszer művelet).
3.  **Persistence**: Az eredmény elmentődik az SQLite-ba.
4.  **State Update**: A Controller frissíti a Store-t.
5.  **Reactive UI**: A UI észleli a változást a Store-ban és automatikusan frissül.

---

## 2. A 5 Rétegű Felépítés (Core-Out)

Az implementáció során a belső magtól (adat) haladunk kifelé (felület).

### I. Réteg: Domain Models (A Mag)
Tisztán Python `dataclasses`, amik az entitásokat reprezentálják. Nincs bennük logika, csak adat.
- `MediaFile`, `Movie`, `Episode`, `Season`

### II. Réteg: AppState (A Tároló)
A `QObject` alapú központi tároló.
- **Tartalma**: Aktuális listák, beállítások, folyamatjelző állapotok.
- **Kommunikáció**: PySide Signal-ok minden változásnál (pl. `files_changed`).

### III. Réteg: Infrastructure (A Perzisztencia)
Adatbázis repozitóriumok és API kliensek.
- **Felelőssége**: Csak az adatok mozgatása a külső források (TMDB, SQLite) és a program között.

### IV. Réteg: Controllers (A Logika)
Itt él a "Pipeline". `async/await` alapú vezérlők.
- Meghívják az Infrastructure réteget.
- Kezelik a hibákat.
- Frissítik az AppState-et.

### V. Réteg: UI Views (A Felület)
"Buta" komponensek, amik csak a Store-t figyelik.
- Nem tartalmaznak SQL hívásokat.
- Csak eseményeket küldenek a Controllereknek.

---

## 3. Implementációs Sorrend

Ha újraírnád a programot, ezt az utat kövesd:

1.  **Define Models**: Határozd meg az adatstruktúrát.
2.  **Build Store**: Hozz létre egy üres AppState-et.
3.  **Mock UI**: Csinálj egy egyszerű felületet, ami a Store-ból dolgozik (akár kamu adatokkal).
4.  **Async Infrastructure**: Írd meg az API és DB kezelőket.
5.  **Connect Controllers**: Írd meg a logikát, ami összeköti a DB-t a Store-ral.

---

## 4. Kód Példa: A Reaktív Lánc

```python
# 1. Controller elindítja a munkát
async def start_identification(self, file_id):
    # Logika fut a háttérben
    result = await self.api.identify(file_id)
    
    # Mentés a DB-be
    await asyncio.to_thread(self.db.save_match, result)
    
    # Store frissítése (Ez triggereli a UI-t)
    self.store.update_file_status(file_id, "Matched")

# 2. UI csak figyel
class FileRow(QWidget):
    def __init__(self, file_id, store):
        self.store = store
        self.store.state_changed.connect(self.refresh)
        
    def refresh(self):
        # Automatikusan lefut, ha a Store változik
        status = self.store.get_status(self.file_id)
        self.status_icon.setIcon(status)
```

---

## 5. Miért ez a "Top Tier"?

*   **Nulla UI Freeze**: Az `asyncio` és `QThread` kombinációja garantálja a folyékony felületet.
*   **Könnyű Debug**: Ha rossz adat jelenik meg, tudod, hogy a Store-ban van a hiba, nem kell 10 különböző UI komponenst átnézni.
*   **Bővíthetőség**: Bármikor hozzáadhatsz egy új nézetet (pl. egy Dashboard-ot), ami ugyanazt a Store-t figyeli, és azonnal működni fog.

> [!TIP]
> Használj **qasync**-et a Python asyncio és a Qt eseményhurok összefésülésére. Ez lehetővé teszi, hogy `await` kulcsszót használj közvetlenül a UI gomboknál is.
