# Investigación de personaje para la Fábrica de Personajes MYIA (investigacion/v1, tipo «personaje»)

Eres Argon. Tarea: investigar el CUERPO (no la personalidad) de un personaje para el motor Blender de MYIA y entregar, en un solo JSON:
(a) la identificación del tipo de cuerpo y su análogo real; (b) los datos de forma, proporciones, articulaciones y movimiento, cada uno con su evidencia; (c) la ficha de esqueleto (ficha_esqueleto/v1); (d) el catálogo de AL MENOS 60 movimientos que ese cuerpo puede hacer.

## ADN del personaje (VARIABLE: datos sellados del canal; mandan sobre cualquier fuente)
1. Ficha Antropométrica:
* **Edad visual:** Polluelo / ave infantil.
* **Estatura aparente:** 18 cm (escala mascota de hombro).
* **Complexión física:** Rechoncha, compacta y redondeada, con silueta en forma de pera.
* **Proporción en cabezas:** 2 cabezas de alto (la cabeza representa el 50% de la altura total).
* **Estilo de línea/sombreado:** 3D CGI estilizado sin línea de contorno. Sombreado suave con dispersión subsuperficial cálida, volúmenes plásticos limpios y textura mate sedosa.

2. Fisonomía Facial y Cabello:
* **Forma del rostro:** Esférica, fusionada directamente con el torso sin cuello divisorio, con mejillas abultadas y rubor anaranjado difuso.
* **Cabello (Cresta):** Penacho central rígido compuesto por 3 plumas curvas de puntas redondeadas en color naranja rojizo (#FF6B2B).
* **Geometría de ojos:** Grandes y circulares; esclerótica blanca, iris marrón cálido, pupila negra concéntrica y un único brillo especular blanco arriba a la izquierda.
* **Grosor de cejas:** Medias, flotantes sobre el plumaje, de color marrón oscuro y bordes redondeados.
* **Accesorios faciales fijos:** Sin accesorios. Pico corto, cónico y pequeño en el centro del rostro, color naranja medio.

3. Paleta de Expresiones:
* **Normal:** Cejas en arco suave simétrico, ojos abiertos al 100% mirando al frente, pico cerrado dibujando una sonrisa curva sutil.
* **Feliz:** Cejas altas arqueadas, ojos cerrados formando dos arcos invertidos oscuros, pico abierto mostrando el interior bucal y lengua rosada.
* **Nervioso:** Cejas oblicuas elevadas en el centro, ojos muy abiertos con el iris contraído, pico entreabierto con comisuras bajas, acompañado de 4 gotas de sudor celestes flotando a los lados de la cabeza.
* **Enojado:** Cejas fruncidas en ángulo "V" pronunciado hacia el entrecejo, párpados superiores rectos cubriendo un tercio del ojo, pico completamente abierto en forma trapezoidal mostrando lengua e interior oscuro.
* **Triste:** Cejas caídas hacia los extremos exteriores, párpados superiores bajos a media asta con mirada descendente, pico cerrado con comisura arqueada hacia abajo.

4. Vestuario por Capas:
* **Prenda exterior (Plumaje corporal):** Cuerpo desnudo cubierto de plumaje liso amarillo brillante (#FFD84D) de aspecto suave y continuo.
* **Prenda interior (Pecho):** Detalle escultórico de 4 puntas de plumas superpuestas en relieve sobre la parte superior del pecho, del mismo tono amarillo (#FFD84D).
* **Prenda inferior (Alas y Cola):** Alas cortas integradas a los costados, amarillas en la base con 3 plumas primarias en color naranja rojizo (#FF6B2B) en los extremos. Cola corta trasera formada por 3 plumas naranjas rojizas.
* **Calzado (Patas):** Patas aviares cortas y delgadas de textura lisa color naranja amarronado, con 3 dedos frontales redondeados y 1 espolón trasero corto sin uñas diferenciadas.

5. Reglas de Giro:
* **De frente:** Visibles las 4 ondas de plumas en el pecho; las alas se ven pegadas al cuerpo mostrando solo el borde de las puntas naranjas; la cola queda completamente oculta tras el cuerpo.
* **De perfil:** Silueta en "S" compacta con pecho prominente; la cresta revela sus 3 plumas escalonadas apuntando hacia atrás; el ala muestra claramente su división bicolor (hombro amarillo, 3 plumas inferiores naranjas); la cola sobresale en ángulo de 45 grados.
* **De espaldas:** Cabeza y espalda completamente lisas en amarillo (#FFD84D) sin costuras ni plumas detalladas; la cola se despliega como un abanico simétrico de 3 pétalos naranjas en la base de la espalda, flanqueada por las puntas naranjas de ambas alas.

## Protocolo (obligatorio, en este orden)
1. IDENTIFICAR: clase de cuerpo (humano, ave, cuadrúpedo, pez, serpiente, criatura, objeto mágico), si es ficticio y su altura en metros (de la hoja).
2. REFERENCIA REAL: si es real, su especie; si es ficticio, 1 o 2 animales reales análogos con `por_que` y `que_cambia`.
3. ESQUELETO Y ARTICULACIONES: huesos o grupos que necesita para actuar, cómo se conectan y el rango de giro ACTIVO normal de cada articulación del análogo, con evidencia.
4. FORMA Y PROPORCIONES: cabeza, tronco, extremidades, alas, cola… como fracción de la altura. Manda la HOJA; la fuente solo completa lo que la hoja no dice.
5. MOVIMIENTO: cómo camina, corre, salta, gira, se sienta, se agacha, patea, vuela o nada ese cuerpo (apoyos, ritmo, qué articulaciones mandan), con evidencia.
6. CATÁLOGO ≥ 60 MOVIMIENTOS: locomoción, posturas, gestos y acciones del ADN. Cada uno: nombre único snake_case, categoría, ciclo (sí/no), duración típica en segundos, huesos que mandan, apoyos en el suelo, y `evidencia` (claves de `datos` que lo justifican). En ESTA llamada NO se piden las poses clave cuadro a cuadro (eso va en otra llamada sin búsqueda).
7. FICHA DE ESQUELETO: `payload.ficha_esqueleto` cumple ficha_esqueleto/v1 (abajo) con TODAS sus reglas (unidades en fracción de altura, ejes, simetría, límites, piezas primitivas, rostro con ojos y nariz/pico).

## Reglas de evidencia (un programa sin IA las comprueba y RECHAZA la respuesta si falla una)
E1. Usa SOLO el CORPUS de abajo como fuente externa. Cada fuente tiene id (F01, F02…), título y URL.
E2. Todo dato medible (rango en grados, proporción, longitud, ritmo) va en `datos` con `origen`:
    - `fuente`: `fuente_id` + `cita` = frase LITERAL de 8–300 caracteres copiada EXACTA del texto de esa fuente;
    - `hoja`: `campo_hoja` = campo del ADN;
    - `deduccion`: `deriva_de` = claves de otros datos + `razon` (p. ej. adaptar el rango del pollito real a un personaje chibi).
E3. Si el corpus no trae un dato, NO lo inventes ni cites de memoria: ponlo como `deduccion` explícita o en `vacios`.
E4. No inventes URLs ni fuentes fuera del corpus. `origen.fecha` de la ficha = 2026-11-09.
E5. Responde SOLO con UN objeto JSON válido (investigacion/v1). Sin texto antes ni después, sin ``` .

## ESQUEMA investigacion/v1
{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"investigacion/v1",
 "title":"Investigación MYIA v1 (sobre común para personaje, objeto, objeto_usuario, escenario)",
 "description":"Cada dato medible lleva su evidencia: fuente_id del CORPUS (F01…) + cita LITERAL copiada del texto de esa fuente; o hoja (campo del ADN) o deduccion (de qué datos sale). Un programa sin IA comprueba que cada cita está en el corpus.",
 "type":"object",
 "required":["schema","tipo","id","nombre","identificacion","datos","vacios","payload"],
 "properties":{
  "schema":{"type":"string","const":"investigacion/v1"},
  "tipo":{"type":"string","enum":["personaje","objeto","objeto_usuario","escenario"]},
  "id":{"type":"string"},"nombre":{"type":"string"},
  "identificacion":{"type":"object","required":["clase","es_ficticio","altura_o_tamano_m","analogos"],
   "properties":{"clase":{"type":"string","description":"humano, ave, cuadrupedo, pez, serpiente, criatura, mueble, vehiculo, edificio, calle, bosque…"},
    "es_ficticio":{"type":"boolean"},
    "altura_o_tamano_m":{"type":"number"},
    "analogos":{"type":"array","items":{"type":"object","required":["nombre","por_que","que_cambia"],"properties":{"nombre":{"type":"string"},"por_que":{"type":"string"},"que_cambia":{"type":"string"}}}}}},
  "datos":{"type":"array","minItems":1,"items":{"type":"object","required":["clave","valor","origen"],
   "properties":{"clave":{"type":"string","description":"ruta del dato, p. ej. proporcion.cabeza, rango.tobillo_L.x, receta.pieza.tablero.ancho"},
    "valor":{},"unidad":{"type":["string","null"]},
    "origen":{"type":"string","enum":["fuente","hoja","deduccion"]},
    "fuente_id":{"type":["string","null"],"description":"F01… si origen=fuente"},
    "cita":{"type":["string","null"],"description":"frase LITERAL (8–300 caracteres) copiada de la fuente que respalda el dato"},
    "campo_hoja":{"type":["string","null"],"description":"si origen=hoja: campo del ADN"},
    "deriva_de":{"type":"array","items":{"type":"string"},"description":"si origen=deduccion: claves de los datos de los que sale"},
    "razon":{"type":"string"}}}},
  "vacios":{"type":"array","items":{"type":"string"},"description":"lo que NO se encontró en el corpus (no se inventa)"},
  "payload":{"type":"object","description":"personaje: {ficha_esqueleto (ficha_esqueleto/v1), catalogo_movimientos[≥60]}; objeto/objeto_usuario: {receta_piezas}; escenario: {piezas_escenario[]}"}
 }}


## ESQUEMA ficha_esqueleto/v1 (para payload.ficha_esqueleto) y sus reglas
## Reglas de la ficha (obligatorias; un programa las comprueba y rechaza la ficha si falla una)
1. Responde SOLO con UN objeto JSON válido que cumpla el ESQUEMA de abajo. Sin texto antes ni después, sin comentarios, sin ``` .
2. Unidades: TODAS las coordenadas, radios y largos son FRACCIONES de `altura_m` (1.0 = altura total en reposo). No uses metros.
3. Ejes del cuerpo en reposo: +Z arriba, −Y = frente (hacia donde mira), +X = lado IZQUIERDO del personaje (sufijo `_L`), −X = derecho (`_R`). Suelo en z = 0; lo que apoya (patas/dedos) llega a z ≈ 0; el punto más alto de las PIEZAS queda en z ≈ 1.0 (0.9–1.1).
4. Árbol: exactamente UNA raíz (`padre: null`, rol `raiz`, en el suelo). Nombres únicos `[A-Za-z][A-Za-z0-9_]*`. Cada hijo empieza a ≤ 0.12 de la cabeza o cola de su padre (salvo hijos directos de la raíz). Largo de cada hueso entre 0.005 y 1.2.
5. Simetría: cada hueso `_L` tiene su `_R` con cabeza/cola de x negada, mismo rol y padre espejado. Huesos `C` en x = 0.
6. Límites de giro `limites_deg` en grados, por eje del cuerpo, aplicados en la cabeza del hueso y en el marco del padre (orden XYZ, 0 = reposo): x = cabeceo (+x lleva hacia el frente −Y lo que está ARRIBA de la articulación y hacia atrás lo que está ABAJO), y = alabeo lateral, z = giro horizontal (+z gira el frente hacia +X). Cada rango [min, max] con −180 ≤ min ≤ 0 ≤ max ≤ 180 y amplitud ≤ 270. Espejo para `_R`: x igual; y y z negados e intercambiados (si L.y = [a, b], R.y = [−b, −a]).
7. Rangos de movimiento: usa valores anatómicos reales (rango activo normal del animal sano, no el máximo forzado). En `funcion` di qué hueso/grupo real representa cada hueso.
8. Piezas: SOLO primitivas `esfera, capsula, cilindro, cono, caja, toro`. `modo: "hueso"` (capsula/cilindro/cono a lo largo del hueso, con `radio`) o `modo: "libre"` (`centro`, `radios` [rx,ry,rz] = semiejes, `rotacion_deg`). Cada pieza va pegada a UN hueso y su centro a ≤ 0.4 de él. Colores `#RRGGBB`.
9. Rostro: `rostro.hueso` = el hueso de rol `cabeza`; `ojos.centro_L` con x > 0 (el R se espeja solo) delante (−Y) del centro de la cabeza; `nariz` (o pico) centrada x = 0, delante de los ojos. Sirven para que la IA de video sepa hacia dónde mira: no hace falta más detalle facial.
10. `poses_prueba`: 2 o 3 poses útiles para animación del personaje, `{nombre: {hueso: [x,y,z]}}` dentro de los límites.
11. Fuentes: en `fuentes` cita de dónde sale cada dato (anatomía, rangos, proporciones). Tipos: `web` (con `url` http(s) que exista; NO inventes URLs: si no estás seguro de la URL usa `conocimiento` con `url: null` y nombra la obra/autor), `conocimiento`, `hoja_personaje`, `deduccion`. Las fuentes de la ficha salen del CORPUS (tipo `web` con la URL de la fuente Fxx).
12. `origen`: `{"tipo":"argon","autor":"Argon","fecha":"<AAAA-MM-DD>"}`. `schema` = "ficha_esqueleto/v1".
13. Nivel de detalle: maniquí para pose y cámara (lo que usa la IA de video como guía), no modelo final. Prefiere pocas piezas bien puestas a muchas. Huesos: los necesarios para que el personaje haga sus acciones, sin dedos individuales salvo que el animal los use para actuar.

## ESQUEMA JSON (ficha_esqueleto/v1)
{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"ficha_esqueleto/v1","title":"Ficha de esqueleto MYIA v1","description":"Unidades: fracción de altura_m. Ejes: +Z arriba, -Y frente, +X izquierda del personaje (L). Suelo z=0, punto más alto de las piezas z≈1. Límites en grados en ejes del cuerpo en reposo (x cabeceo, y alabeo, z giro), orden XYZ, 0=reposo. Espejo L→R: x negado; límite x igual; y,z negados e intercambiados.","type":"object","required":["schema","id","nombre","plantilla","es_ficticio","analogo_real","altura_m","origen","fuentes","huesos","piezas","rostro","poses_prueba"],"properties":{"schema":{"type":"string","const":"ficha_esqueleto/v1"},"id":{"type":"string"},"nombre":{"type":"string"},"plantilla":{"type":"string","enum":["bipedo_humano","ave","cuadrupedo","pez","serpiente","objeto_magico","otro"]},"es_ficticio":{"type":"boolean"},"analogo_real":{"type":["string","null"],"description":"animal real del que se deduce el esqueleto si es ficticio"},"altura_m":{"type":"number","minimum":0.01,"maximum":30},"origen":{"type":"object","required":["tipo","autor","fecha"],"properties":{"tipo":{"type":"string","enum":["EJEMPLO_MANUAL","argon"]},"autor":{"type":"string"},"fecha":{"type":"string"},"aviso":{"type":"string"}}},"fuentes":{"type":"array","minItems":1,"items":{"type":"object","required":["tipo","titulo","url","afirma"],"properties":{"tipo":{"type":"string","enum":["web","conocimiento","hoja_personaje","deduccion"]},"titulo":{"type":"string"},"url":{"type":["string","null"]},"afirma":{"type":"string"}}}},"huesos":{"type":"array","minItems":2,"items":{"type":"object","required":["nombre","padre","cabeza","cola","rol","lado","limites_deg","funcion"],"properties":{"nombre":{"type":"string","pattern":"^[A-Za-z][A-Za-z0-9_]{0,62}$"},"padre":{"type":["string","null"]},"cabeza":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"cola":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"rol":{"type":"string","enum":["raiz","cadera","columna","pecho","cuello","cabeza","mandibula","pico","oreja","copete","cola","hombro","brazo","antebrazo","mano","ala","pierna","pie","dedos","pata_delantera","pata_trasera","aleta","otro"]},"lado":{"type":"string","enum":["C","L","R"]},"limites_deg":{"type":"object","required":["x","y","z"],"properties":{"x":{"type":"array","items":{"type":"number"},"minItems":2,"maxItems":2},"y":{"type":"array","items":{"type":"number"},"minItems":2,"maxItems":2},"z":{"type":"array","items":{"type":"number"},"minItems":2,"maxItems":2}}},"funcion":{"type":"string","description":"hueso o grupo anatómico real que representa"}}}},"piezas":{"type":"array","minItems":1,"items":{"type":"object","required":["nombre","hueso","primitiva","modo","color"],"properties":{"nombre":{"type":"string"},"hueso":{"type":"string"},"primitiva":{"type":"string","enum":["esfera","capsula","cilindro","cono","caja","toro"]},"modo":{"type":"string","enum":["hueso","libre"],"description":"hueso: capsula/cilindro/cono a lo largo del hueso con 'radio'; libre: 'centro'+'radios'(+rotacion_deg)"},"radio":{"type":"number"},"centro":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"radios":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"rotacion_deg":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"color":{"type":"string","pattern":"^#[0-9A-Fa-f]{6}$"}}}},"rostro":{"type":"object","required":["hueso","ojos","nariz"],"properties":{"hueso":{"type":"string"},"ojos":{"type":"object","required":["centro_L","radio"],"properties":{"centro_L":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"radio":{"type":"number"}}},"nariz":{"type":"object","required":["centro","radio","primitiva"],"properties":{"centro":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"radio":{"type":"number"},"primitiva":{"type":"string","enum":["esfera","cono"]},"color":{"type":"string"},"nota":{"type":"string"}}}}},"poses_prueba":{"type":"object","description":"{nombre_pose: {hueso: [x,y,z] grados}}","additionalProperties":{"type":"object","additionalProperties":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3}}}}}

## Formato de un hueso (ilustración de formato, NO son datos a copiar)
{"nombre":"femur_L","padre":"cadera","cabeza":[0.09,0.28,0.66],"cola":[0.10,0.20,0.42],"rol":"pata_trasera","lado":"L","limites_deg":{"x":[-60,40],"y":[-15,15],"z":[-15,15]},"funcion":"fémur"}


## Formato de un movimiento del catálogo (ilustración, NO son datos a copiar)
{"nombre":"saltito_dos_patas","categoria":"locomocion","ciclo":false,"duracion_s":0.6,"huesos_mandan":["tibiotarso_L","tibiotarso_R","tarso_L","tarso_R"],"apoyos":["dedos_L","dedos_R"],"evidencia":["movimiento.salto.impulso"]}

## CORPUS (VARIABLE: descargado por el recolector de MYIA; archivo y sha256 en el registro de la llamada)
### F01 | Bird anatomy | https://en.wikipedia.org/wiki/Bird_anatomy | CC BY-SA 4.0 (Wikipedia)
Bird anatomy, or the physiological structure of birds' bodies, shows many unique adaptations, mostly aiding flight. Birds have a light skeletal system and light but powerful musculature which, along with circulatory and respiratory systems capable of very high metabolic rates and oxygen supply, permit the bird to fly. The development of a beak has led to evolution of a specially adapted digestive system.


== Skeletal system ==

Birds have many bones that are hollow (pneumatized) with criss-crossing struts or trusses for structural strength. The number of hollow bones varies among species, though large gliding and soaring birds tend to have the most. Respiratory air sacs often form air pockets within the semi-hollow bones of the bird's skeleton. The bones of diving birds are often less hollow than those of non-diving species. Penguins, loons, puffins, and kiwis are without pneumatized bones entirely. Flightless birds, such as ostriches and emus, have pneumatized femurs and, in the case of the emu, pneumatized cervical vertebrae.
In most birds, non-pneumatized bones are filled with bone marrow.


=== Axial skeleton ===
The bird skeleton is highly adapted for flight. It is extremely lightweight but strong enough to withstand the stresses of taking off, flying, and landing. One key adaptation is the fusing of bones into single ossifications, such as the pygostyle. Because of this, birds usually have a smaller number of bones than other terrestrial vertebrates. Birds also lack teeth or even a true jaw and instead have a beak, which is far more lightweight. The beaks of many baby birds have a projection called an egg tooth, which facilitates their exit from the amniotic egg. It falls off once the egg has been penetrated.


==== Vertebral column ====
The vertebral column is divided into five sections of vertebrae:


===== Cervical vertebrae =====
The cervical vertebrae provide structural support to the neck and number between 8 and as many as 25 vertebrae in certain swan species (Cygninae) and other long-necked birds. All cervical vertebrae have transverse processes attached except the first one. This vertebra (C1) is called the atlas which articulates with the occipital condyles of the skull and lacks the foramen typical of most vertebrae. The neck of a bird is composed of many cervical vertebrae enabling birds to have increased flexibility. A flexible neck allows many birds with immobile eyes to move their head more productively and center their sight on objects that are close or far in distance. Most birds have about three times as many neck vertebrae as humans, which allows for increased stability during fast movements such as flying, landing, and taking-off. The neck plays a role in head-bobbing which is present in at least eight out of 44 orders of birds, including Columbiformes, Galliformes, and Gruiformes. Head-bobbing is an optokinetic response which stabilizes a bird's surroundings as it alternates between a thrust phase and a hold phase. Head-bobbing is synchronous with the feet as the head moves in accordance with the rest of the body. Data from various studies suggest that the main reason for head-bobbing in some birds is for the stabilization of their surroundings, although it is uncertain why some but not all bird orders show head-bob.


===== Thoracic vertebrae =====
The thoracic vertebrae number between five and ten, and the first thoracic vertebra is distinguishable due to the fusion of its attached rib to the sternum while the ribs of cervical vertebrae are free. Anterior thoracic vertebrae are fused in many birds and articulate with the notarium of the pectoral girdle.


===== Synsacrum =====
The synsacrum consists of one thoracic, six lumbar, two sacral, and five sacro-caudal vertebrae fused into one ossified structure that then fuse with the ilium.  When not in flight, this structure provides the main support for the rest of the body. Similar to the sacrum of mammals, the synsacrum lacks the distinct disc shape of cervical and thoracic vertebrae.


===== Caudal vertebrae =====
The free vertebrae immediately following the fused sacro-caudal vertebrae of the synsacrum are known as the caudal vertebrae. Birds have between five and eight free caudal vertebrae. The caudal vertebrae provide structure to the tails of vertebrates and are homologous to the coccyx found in mammals lacking tails.


===== Pygostyle =====
In birds, the last four caudal vertebrae are fused to form the pygostyle. Some sources note that up to ten caudal vertebrae may make up this fused structure. This structure provides an attachment point for tail feathers that aid in control of flight.


==== Scapular girdle ====
Birds are the only living vertebrates to have fused collarbones and a keeled breastbone. The keeled sternum serves as an attachment site for the muscles used in flying or swimming. Flightless birds, such as ostriches, lack a keeled sternum and have denser and heavier bones compared to birds that fly. Swimming birds have a wide sternum, walking birds have a long sternum, and flying birds have a sternum that is nearly equal in width and height. The chest consists of the furcula (wishbone) and coracoid (collar bone) which, together with the scapula, form the pectoral girdle; the side of the chest is formed by the ribs, which meet at the sternum (mid-line of the chest).


==== Ribs ====
Birds have uncinate processes on the ribs. These are hooked extensions of bone which help to strengthen the rib cage by overlapping with the rib behind them. This feature is also found in the tuatara (Sphenodon).


==== Skull ====

The skull consists of five major bones: the frontal (top of head), parietal (back of head), premaxillary and nasal (top beak), and the mandible (bottom beak). The skull of a normal bird usually weighs about 1% of the bird's total body weight. The eye occupies a considerable amount of the skull and is surrounded by a scleral ring, a ring of tiny overlapping bones. This ring is also seen in non-avian reptiles and various other vertebrates.
Broadly speaking, avian skulls consist of many small, non-overlapping bones. Pedomorphosis, maintenance of the ancestral state in adults, is thought to have facilitated the evolution of the avian skull. In essence, adult bird skulls will resemble the juvenile form of their theropod dinosaur ancestors. As the avian lineage has progressed and as pedomorphosis has occurred, they have lost the postorbital bone behind the eye, the ectopterygoid at the back of the palate, and teeth. The palate structures have also become greatly altered with changes, mostly reductions, seen in the pterygoid, palatine, and jugal bones. A reduction in the adductor chambers has also occurred. These are all conditions seen in the juvenile form of their ancestors. The premaxillary bone has also hypertrophied to form the beak while the maxilla has become diminished, as suggested by both developmental and paleontological  studies. This expansion into the beak has occurred in tandem with the loss of a functional hand and the developmental of a point at the front of the beak that resembles a "finger". The premaxilla is also known to play a large role in feeding behaviours in fish.
The structure of the avian skull has important implications for their feeding behaviours. Birds show independent movement of the skull bones known as cranial kinesis. Cranial kinesis in birds occurs in several forms, but all of the different varieties are all made possible by the anatomy of the skull. Animals with large, overlapping bones (including the ancestors of modern birds) have akinetic (non-kinetic) skulls. For this reason it has been argued that the pedomorphic bird beak can be seen as an evolutionary innovation.
Birds have a diapsid skull, as in reptiles, with a pre-lachrymal fossa (present in some reptiles). The skull has a single occipital condyle.


=== Appendicular skeleton ===

The shoulder consists of the scapula (shoulder blade), coracoid, and humerus (upper arm). The humerus joins the radius and ulna (forearm) to form the elbow. The carpus and metacarpus form the "wrist" and "hand" of the bird, and the digits are fused together. The bones in the wing are extremely light so that the bird can fly more easily.
The hips consist of the pelvis, which includes three major bones: the ilium (top of the hip), ischium (sides of hip), and pubis (front of the hip). These are fused into one (the innominate bone). Innominate bones are evolutionary significant in that they allow birds to lay eggs. They meet at the acetabulum (hip socket) and articulate with the femur, which is the first bone of the hind limb.
The upper leg consists of the femur. At the knee joint, the femur connects to the tibiotarsus (shin) and fibula (side of lower leg). The tarsometatarsus forms the upper part of the foot, digits make up the toes. The leg bones of birds are the heaviest, contributing to a low center of gravity, which aids in flight. A bird's skeleton accounts for only about 5% of its total body weight.
They have a greatly elongate tetradiate pelvis, similar to some reptiles. The hind limb has an intra-tarsal joint found also in some reptiles. There is extensive fusion of the trunk vertebrae as well as fusion with the pectoral girdle.


==== Wings ====


==== Feet ====

Birds' feet are classified as anisodactyl, zygodactyl, heterodactyl, syndactyl or pamprodactyl. Anisodactyl is the most common arrangement of digits in birds, with three toes forward and one back. This is common in songbirds and other perching birds, as well as hunting birds like eagles, hawks, and falcons.
Syndactyly, as it occurs in birds, is like anisodactyly, except that the second and third toes (the inner and middle forward-pointing toes), or three toes, are fused together, as in the belted kingfisher Ceryle alcyon. This is characteristic of Coraciiformes (kingfishers, bee-eaters, rollers, etc.).
Zygodactyl (from Greek ζυγον, a yoke) feet have two toes facing forward (digits two and three) and two back (digits one and four). This arrangement is most common in arboreal species, particularly those that climb tree trunks or clamber through foliage. Zygodactyly occurs in the parrots, woodpeckers (including flickers), cuckoos (including roadrunners), and some owls. Zygodactyl tracks have been found dating to 120–110 Ma (early Cretaceous), 50 million years before the first identified zygodactyl fossils.
Heterodactyly is like zygodactyly, except that digits three and four point forward and digits one and two point back. This is found only in trogons, while pamprodactyl is an arrangement in which all four toes may point forward, or birds may rotate the outer two toes backward. It is a characteristic of swifts (Apodidae).


=== Evolution ===


==== Hind limb change ====
A significant similarity in the structure of the hind limbs of birds and other dinosaurs is associated with their ability to walk on two legs, or bipedalism. In the 20th century, the prevailing opinion was that the transition to bipedalism occurred due to the transformation of the forelimbs into wings. Modern scientists believe that, on the contrary, it was a necessary condition for the occurrence of flight.

The transition to the use of only the hind limbs for movement was accompanied by an increase in the rigidity of the lumbar and sacral regions. The pubic bones of birds and some other bipedal dinosaurs are turned backward. Scientists associate this with a shift in the center of gravity of the body backward. The reason for this shift is called the transition to bipedality or the development of powerful forelimbs, as in Archaeopteryx. The large and heavy tail of two-legged dinosaurs may have been an additional support. Partial tail reduction and subsequent formation of pygostyle occurred due to the backward deviation of the first toe of the hind limb; in dinosaurs with a long rigid tail, the development of the foot proceeded differently. This process, apparently, took place

### F02 | Chicken | https://en.wikipedia.org/wiki/Chicken | CC BY-SA 4.0 (Wikipedia)
The chicken (Gallus gallus domesticus) is the domesticated subspecies of the red junglefowl (Gallus gallus), originally native to Southeast Asia. It was first domesticated around 8,000 years ago and is one of the most common and widespread domesticated animals in the world. Chickens are primarily cultivated as poultry for their meat and eggs, and are occasionally kept as pets.
As of 2023, the global live population of chicken exceeded 26.5 billion, with more than 50 billion birds slaughtered annually for consumption. Specialized breeds such as broilers and laying hens have been developed for better meat and egg yield, respectively. A female chicken (known as a hen) bred for egg production can lay over 300 eggs per year. Chickens are social animals with dominance hierarchy (known colloquially as "pecking order"), complex vocalizations and social behaviors, and feature in folklore, religion and literature across many societies. Their economic importance makes them a central component of global animal husbandry.


== Etymology ==
The word chicken comes from Old English ċicen (pronounced essentially the same as in Modern English). While the origin is Germanic, it is unclear exactly where the word came from, although it could ultimately have come from an imitation of the sound a chicken makes.


== Nomenclature ==
Terms for chickens include:

Biddy: a chicken, or a newly hatched chicken
Capon: a castrated or neutered male chicken
Chick: a young chicken
Chook : a chicken (Australia/New Zealand, informal)
Cock: a fertile adult male chicken
Cockerel: a young male chicken
Hen: an adult female chicken
Pullet: a young female chicken less than a year old. In the poultry industry, a pullet is a sexually immature chicken less than 22 weeks of age.
Rooster: a fertile adult male chicken, especially in North America. Originated in the 18th century, possibly as a euphemism to avoid the sexual connotation of the word cock.
Yardbird: a chicken (southern United States, dialectal)
Chicken can mean a chick, and this was historically the meaning of the word chicken, as in William Shakespeare's play Macbeth, where Macduff laments the death of "all my pretty chickens and their dam". The usage is preserved in placenames such as the Hen and Chicken Islands. In older sources, and still often in trade and scientific contexts, chickens as a species are described as common fowl or domestic fowl.


== Description ==

Chickens are relatively large birds, active by day. The body is round, the legs are unfeathered in most breeds, and the wings are short. Wild junglefowl can fly, whereas domestic chickens and their flight muscles are too heavy to allow them to fly more than a short distance. Size and coloration vary widely between breeds. Newly hatched chicks of both modern and heritage varieties weigh the same, about 37 g (1.3 oz). Modern varieties however grow much faster; by day 35 a Ross 708 broiler may weigh 1.8 kg (4.0 lb) as against the 1.05 kg (2.3 lb) of a heritage chicken of the same age.
Adult chickens of both sexes have a fleshy crest on their heads called a comb or cockscomb, and hanging flaps of skin on either side under their beaks called wattles; combs and wattles are more prominent in males. Some breeds have a mutation that causes extra feathering under the face, giving the appearance of a beard.
Chickens are omnivores. In the wild, they scratch at the soil to search for seeds, insects, and animals as large as lizards, small snakes, and young mice. A chicken may live for 5–10 years, depending on the breed. The world's oldest known chicken lived for 16 years.
Chickens are gregarious, living in flocks, and incubate eggs and raise young communally. Individual chickens dominate others, establishing a pecking order; dominant individuals take priority for access to food and nest sites. The concept of dominance, involving pecking, was described in female chickens by Thorleif Schjelderup-Ebbe in 1921 as the "pecking order". Male chickens tend to leap and use their claws in conflicts. Chickens are capable of mobbing and killing a weak or inexperienced predator, such as a young fox. Chickens have been thought of primarily as providers of food, but their cognition, emotions, and sociality are comparable with other birds and mammals.

A male's crowing is a loud and sometimes shrill call, serving as a territorial signal to other males, and in response to sudden disturbances within their surroundings. Hens cluck loudly after laying an egg and to call their chicks. Chickens give different warning calls to indicate that a predator is approaching from the air or on the ground.


== Reproduction and life-cycle ==
To initiate courting, some roosters may dance in a circle around or near a hen (a circle dance), often lowering the wing which is closest to the hen. The dance triggers a response in the hen and when she responds to his call, the rooster may mount the hen and proceed with the mating. Mating typically involves a sequence in which the male approaches the female and performs a waltzing display. If the female is unreceptive, she runs off; otherwise, she crouches, and the male mounts, treading with both feet on her back. After copulation the male does a tail-bending display.

Sperm transfer occurs by cloacal contact between the male and female, in an action called the 'cloacal kiss'. As with all birds, reproduction is controlled by a neuroendocrine system, the Gonadotropin-Releasing Hormone-I neurons in the hypothalamus. Reproductive hormones including estrogen, progesterone, and gonadotropins (luteinizing hormone and follicle-stimulating hormone) initiate and maintain sexual maturation changes. Reproduction declines with age, thought to be due to a decline in GnRH-I-N.
Hens often try to lay in nests that already contain eggs and sometimes move eggs from neighboring nests into their own. A flock thus uses only a few preferred locations, rather than having a different nest for every bird. Under natural conditions, most birds lay only until a clutch is complete; they then incubate all the eggs. This is called "going broody". The hen sits on the nest, fluffing up or pecking defensively if disturbed. She rarely leaves the nest until the eggs have hatched.

Eggs of chickens from the high-altitude region of Tibet have special physiological adaptations that result in a higher hatching rate in low oxygen environments. When eggs are placed in a hypoxic environment, chicken embryos from these populations express much more hemoglobin than embryos from other chicken populations. This hemoglobin has a greater affinity for oxygen, binding oxygen more readily.
Fertile chicken eggs hatch at the end of the incubation period, about 21 days; the chick uses its egg tooth to break out of the shell. Hens remain on the nest for about two days after the first chick hatches; during this time the newly hatched chicks feed by absorbing the internal yolk sac. The hen guards her chicks and broods them to keep them warm. She leads them to food and water and calls them towards food. The chicks imprint on the hen and subsequently follow her continually. She continues to care for them until they are several weeks old.
Inbreeding of White Leghorn chickens tends to cause inbreeding depression expressed as reduced egg number and delayed sexual maturity. Strongly inbred Langshan chickens display obvious inbreeding depression in reproduction, particularly for traits such as age when the first egg is laid and egg number.


== Origin ==


=== Phylogeny ===

Water or ground-dwelling fowl similar to modern partridges, in the Galliformes, the order of bird to which chickens belong, survived the Cretaceous–Paleogene extinction event that killed all tree-dwelling birds and their dinosaur relatives. Chickens are descended primarily from the red junglefowl (Gallus gallus) and are scientifically classified as the same species. Domesticated chickens freely interbreed with populations of red junglefowl. The domestic chicken has subsequently hybridised with grey junglefowl, Sri Lankan junglefowl and green junglefowl; a gene for yellow skin, for instance, was incorporated into domestic birds from the grey junglefowl (G. sonneratii). It is estimated that chickens share between 71 and 79% of their genome with red junglefowl.


=== Domestication ===

The red junglefowl is well adapted to take advantage of the vast quantities of seed produced during the end of the multi-decade bamboo seeding cycle, to boost its own reproduction. In domesticating the chicken, humans took advantage of the red junglefowl's ability to reproduce prolifically when exposed to a surge in its food supply.
Exactly when and where the chicken was domesticated was controversial. Genomic studies estimated that the chicken was domesticated 8,000 years ago in Southeast Asia and spread to China and India 2,000 to 3,000 years later. Archaeological evidence appeared to support domestic chickens in Southeast Asia well before 6000 BC, China by 6000 BC and India by 2000 BC. An early study proposed that a single domestication event of the red junglefowl in present-day Thailand gave rise to the modern chicken. A 2020 Nature study that fully sequenced 863 chickens across the world suggests that all domestic chickens originate from a single domestication event of red junglefowl (Gallus gallus) whose present-day distribution is predominantly in Southeast Asia. These domesticated chickens spread across Southeast and South Asia where they interbred with local wild species of junglefowl, forming genetically and geographically distinct groups. Analysis of the most popular commercial breed shows that the White Leghorn breed possesses a mosaic of divergent ancestries inherited from different subspecies of red junglefowl.
Re-examination of bones from over 600 sites, and dating of those from 23 sites, identified the earliest probable chicken bones as from central Thailand, at Ban Non Wat, some 3,250 years ago. The paleo-anatomist Joris Peters and the bioarchaeologist Greger Larson state that this coincided with the growing of rice, and propose that wild jungle fowl were attracted to eat the rice seeds, nested nearby, and became domesticated. Skeletons of birds in the Gallus genus were used as grave goods at the site, confirming domestication.


== Dispersal ==


=== Austronesia ===

A word for the domestic chicken (*manuk) is part of the reconstructed Proto-Austronesian language, indicating they were domesticated by the Austronesian peoples since ancient times. Chickens, together with dogs and pigs, were carried throughout the entire range of the prehistoric Austronesian maritime migrations to Island Southeast Asia, Micronesia, Island Melanesia, Polynesia, and Madagascar, starting from at least 3000 BC from Taiwan. These chickens may have been introduced during pre-Columbian times to South America via Polynesian seafarers, but this is disputed.


=== Africa ===
The earliest evidence of domestic chickens in Africa is at the Pre-Aksumite site Mezber in Ethiopia. These chickens were incorporated into early diets, supported by the presence of human bite marks and cut marks on chicken remains. Supported by archaeological, linguistic, and genetic evidence, these chickens likely arrived to the Horn of Africa through trade networks across the Red Sea. 
Chickens reached Egypt via the Middle East for purposes of cockfighting about 1400 BC and became widely bred in Egypt around 300 BC. Three possible routes of introduction into northern Africa around the early first millennium AD could have been through the Egyptian Nile Valley, the East Africa Roman-Greek or Indian trade, or from Carthage and the Berbers, across the Sahara. Other early known remains are from Mali, Nubia, East Coast, and South Africa and date back to the middle of the first millennium AD.


=== Americas ===

The possibility that domestic chickens were in the Americas before Western contact is debated by researchers, but blue-egged chickens, found only i

### F03 | Precociality and altriciality | https://en.wikipedia.org/wiki/Precociality_and_altriciality | CC BY-SA 4.0 (Wikipedia)
Precocial () species in birds and mammals are those in which the young are relatively mature and mobile from the moment of birth or hatching. They are normally nidifugous, meaning that they leave the nest shortly after birth or hatching. Altricial species are those in which the young are underdeveloped at the time of birth, maturing with the aid of their parents. These categories form a continuum, without distinct gaps between them.

In fish, this often refers to the presence or absence of a stomach: precocial larvae have one at the onset of first feeding whereas altricial fish do not. Depending on the species, the larvae may develop a functional stomach during metamorphosis (gastric) or remain stomachless (agastric).


== Precociality ==

Precocial young have open eyes, hair or down, large brains, and are immediately mobile and somewhat able to flee from or defend themselves against predators. For example, with ground-nesting birds such as ducks or turkeys, the young are ready to leave the nest in one or two days. Among mammals, most ungulates are precocial, being able to walk almost immediately after birth. 


=== Etymology ===
The word "precocial" is derived from the Latin root praecox, the same root as in precocious, meaning early maturity.


=== Superprecociality ===
Extremely precocial species are called "superprecocial". Examples are the megapode birds, which have full-flight feathers at hatching and which, in some species, can fly on the same day. Enantiornithes and pterosaurs were also capable of flight soon after hatching.
Another example is the blue wildebeest, the calves of which can stand within an average of six minutes from birth and walk within thirty minutes; they can outrun a hyena within a day. Such behavior gives them an advantage over other herbivore species and they are 100 times more abundant in the Serengeti ecosystem than hartebeests, their closest taxonomic relative. Hartebeest calves are not as precocial as wildebeest calves and take up to thirty minutes or more before they stand, and as long as forty-five minutes before they can follow their mothers for short distances. They are unable to keep up with their mothers until they are more than a week old.
Black mambas are highly precocial; as hatchlings, they are fully independent, and are capable of hunting prey the size of a small rat.


=== Phylogeny ===
Precociality is thought to be ancestral in birds. Thus, altricial birds tend to be found in the most derived groups. There is some evidence for precociality in protobirds and troodontids. Enantiornithes at least were superprecocial in a way similar to that of megapodes, being able to fly soon after birth. It has been speculated that superprecociality prevented enantiornithines from acquiring specialized toe anatomy seen in modern altricial birds.


== Altriciality ==

In birds and mammals, altricial species are those whose newly hatched or born young are relatively immobile, lack hair or down, are not able to obtain food on their own, and must be cared for by adults; closed eyes are common, though not ubiquitous. Altricial young are born helpless and require care for a length of time. Altricial birds include hawks, herons, woodpeckers, owls, cuckoos and most passerines. Among mammals, marsupials and most rodents are altricial. Domestic cats, dogs, and primates, such as humans, are some of the best-known altricial organisms.  For example, newborn domestic cats cannot see, hear, maintain their own body temperature, or gag, and require external stimulation in order to defecate and urinate. The giant panda is notably the largest placental mammal to have altricial, hairless young upon birth. The larval stage of insect development is considered by some to be a form of altricial development, but it more accurately depicts, especially amongst eusocial animals, an independent phase of development, as the larvae of bees, ants, and many arachnids are completely physically different from their developed forms, and the pre-pupal stages of insect life might be regarded as equivalent to vertebrate embryonic development. 


=== Etymology ===
The word "altriciality" is derived from the Latin root alere, meaning "to nurse, to rear, or to nourish", and indicates the need for young to be fed and taken care of for a long duration.


== Differences ==
The span between precocial and altricial species is particularly broad in the biology of birds. Precocial birds hatch with their eyes open and are covered with downy feathers that are soon replaced by adult-type feathers. Birds of this kind can also swim and run much sooner after hatching than altricial young, such as songbirds. Very precocial birds can be ready to leave the nest in a short period of time following hatching (e.g. 24 hours). Many precocial chicks are not independent in thermoregulation (the ability to regulate their body temperatures), and they depend on the attending parent(s) to brood them with body heat for a short time. Precocial birds find their own food, sometimes with help or instruction from their parents. Examples of precocial birds include the domestic chicken, many species of ducks and geese, waders, rails, and the hoatzin.
Precocial birds can provide protein-rich eggs and thus their young hatch in the fledgling stage – able to protect themselves from predators and the females have less post-natal involvement. Altricial birds are less able to contribute nutrients in the pre-natal stage; their eggs are smaller and their young are still in need of much attention and protection from predators. This may be related to r/K selection; however, this association fails in some cases.
In birds, altricial young usually grow faster than precocial young. This is hypothesized to occur so that exposure to predators during the nestling stage of development can be minimized.
In the case of mammals, it has been suggested that large, hearty adult body sizes favor the production of large, precocious young, which develop with a longer gestation period. Large young may be associated with migratory behavior, extended reproductive period, and reduced litter size. It may be that altricial strategies in mammals, in contrast, develop in species with less migratory and more territorial lifestyles, such as carnivorans, the mothers of which are capable of bearing a fetus in the early stages of development and focusing closely and personally upon its raising, as opposed to precocial animals which provide their youths with a bare minimum of aid and otherwise leave them to instinct.
Human children, and those of other primates, exemplify a unique combination of altricial and precocial development. Infants are born with minimal eyesight, compact and fleshy bodies, and "fresh" features (thinner skin, small noses and ears, and scarce hair if any). However, this stage is brief amongst primates alone; their offspring soon develop stronger bones, grow in spurts, and quickly mature in features. This unique growth pattern allows for the hasty adaptivity of most simians, as anything learned by children in between their infancy and adolescence is memorized as instinct; this pattern is also in contrast to more prominently altricial mammals, such as many rodents, which remain largely immobile and undeveloped until grown to near the stature of their parents.


== Terminology ==
In birds, the terms Aves altrices and Aves precoces were introduced by Carl Jakob Sundevall (1836), and the terms nidifugous and nidicolous by Lorenz Oken in 1816. The two classifications were considered identical in early times, but the meanings are slightly different, in that "altricial" and "precocial" refer to developmental stages, while "nidifugous" and "nidicolous" refer to leaving or staying at the nest, respectively.


== See also ==
Parental investment
Precocious puberty


== References ==


== Bibliography ==
Starck J.M.; Ricklefs R.E. (1998). "Patterns of Development: The Altricial – Precocial Spectrum". Avian Growth and Development. New York: Oxford University Press.


== External links ==

The altricial-precocial spectrum in birds

### F04 | Bird flight | https://en.wikipedia.org/wiki/Bird_flight | CC BY-SA 4.0 (Wikipedia)
Bird flight is the primary mode of locomotion used by most bird species in which birds take off and fly. Flight assists birds with feeding, breeding, avoiding predators, and migrating.
Bird flight includes multiple types of motion, including hovering, taking off, and landing, involving many complex movements. As different bird species adapted over millions of years through evolution for specific environments, prey, predators, and other needs, they developed specializations in their wings, and acquired different forms of flight.
Various theories exist about how bird flight evolved, including flight from falling or gliding (the trees down hypothesis), from running or leaping (the ground up hypothesis), from wing-assisted incline running or from  proavis (pouncing) behavior.


== Basic mechanics of bird flight ==


=== Lift, drag and thrust ===
The fundamentals of bird flight are similar to those of aircraft, in which the aerodynamic forces sustaining flight are lift, drag, and thrust. Lift force is produced by the action of air flow on the wing, which is an airfoil. The airfoil is shaped such that the air provides a net upward force on the wing, while the movement of air is directed downward. Additional net lift may come from airflow around the bird's body in some species, especially during intermittent flight while the wings are folded or semi-folded (cf. lifting body).
Aerodynamic drag is the force opposite to the direction of motion, and hence the source of energy loss in flight. The drag force can be separated into two portions, lift-induced drag, which is the inherent cost of the wing producing lift (this energy ends up primarily in the wingtip vortices), and parasitic drag, including skin friction drag from the friction of air and body surfaces and form drag from the bird's frontal area. The streamlining of bird's body and wings reduces these forces. Unlike aircraft, which have engines to produce thrust, birds flap their wings with a given flapping amplitude and frequency to generate thrust.


== Flight ==
Birds use mainly three types of flight, distinguished by wing motion.


=== Gliding flight ===
When in gliding flight, the upward aerodynamic force is equal to the weight. In gliding flight, no propulsion is used; the energy to counteract the energy loss due to aerodynamic drag is either taken from the potential energy of the bird, resulting in a descending flight, or is replaced by rising air currents ("thermals"), referred to as soaring flight. For specialist soaring birds (obligate soarers), the decision to engage in flight are strongly related to atmospheric conditions that allow individuals to maximise flight-efficiency and minimise energetic costs.


=== Flapping flight ===

When a bird flaps, as opposed to gliding, its wings continue to develop lift as before, but the lift is rotated forward by the flight muscles to provide thrust, which counteracts drag and increases its speed, which has the effect of also increasing lift to counteract its weight, allowing it to maintain height or to climb. Flapping involves two stages: the down-stroke, which provides the majority of the thrust, and the up-stroke, which can also (depending on the bird's wings) provide some thrust. At each up-stroke the wing is slightly folded inwards to reduce the energetic cost of flapping-wing flight. Birds change the angle of attack continuously within a flap, as well as with speed.


=== Bounding flight ===
Small birds often fly long distances using a technique in which short bursts of flapping are alternated with intervals in which the wings are folded against the body. This is a flight pattern known as "bounding" or "flap-bounding" flight. When the bird's wings are folded, its trajectory is primarily ballistic, with a small amount of body lift. The flight pattern is believed to decrease the energy required by reducing the aerodynamic drag during the ballistic part of the trajectory, and to increase the efficiency of muscle use.


=== Hovering ===

Several bird species use hovering, with one family specialized for hovering – the hummingbirds. True hovering occurs by generating lift through flapping alone, rather than by passage through the air, requiring considerable energy expenditure. This usually confines the ability to smaller birds, but some larger birds, such as a kite or osprey can hover for a short period of time. Although not a true hover, some birds remain in a fixed position relative to the ground or water by flying into a headwind. Hummingbirds, kestrels, terns and hawks use this wind hovering.
Most birds that hover have high aspect ratio wings that are suited to low speed flying. Hummingbirds are a unique exception – the most accomplished hoverers of all birds. Hummingbird flight is different from other bird flight in that the wing is extended throughout the whole stroke, which is a symmetrical figure of eight, with the wing producing lift on both the up- and down-stroke. Hummingbirds beat their wings at some 43 times per second, while others may be as high as 80 times per second.


=== Take-off and landing ===
Take-off is one of the most energetically demanding aspects of flight, as the bird must generate enough airflow across the wing to create lift. Small birds do this with a simple upward jump. However, this technique does not work for larger birds, such as albatrosses and swans, which instead must take a running start to generate sufficient airflow. Large birds take off by facing into the wind, or, if they can, by perching on a branch or cliff so they can just drop off into the air.
Landing is also a problem for large birds with high wing loads. This problem is dealt with in some species by aiming for a point below the intended landing area (such as a nest on a cliff) then pulling up beforehand. If timed correctly, the airspeed once the target is reached is virtually nil. Landing on water is simpler, and the larger waterfowl species prefer to do so whenever possible, landing into wind and using their feet as skids. To lose height rapidly prior to landing, some large birds such as geese indulge in a rapid alternating series of sideslips or even briefly turning upside down in a maneuver termed whiffling.


== Wings ==

The bird's forelimbs (the wings) are the key to flight. Each wing has a central vane to hit the wind, composed of three limb bones, the humerus, ulna and radius. The hand, or manus, which ancestrally was composed of five digits, is reduced to three digits (digit II, III and IV or I, II, III depending on the scheme followed), which serves as an anchor for the primaries, one of two groups of flight feathers responsible for the wing's airfoil shape. The other set of flight feathers, behind the carpal joint on the ulna, are called the secondaries. The remaining feathers on the wing are known as coverts, of which there are three sets. The wing sometimes has vestigial claws. In most species, these are lost by the time the bird is adult (such as the highly visible ones used for active climbing by hoatzin chicks), but claws are retained into adulthood by the secretarybird, screamers, finfoots, ostriches, several swifts and numerous others, as a local trait, in a few specimens.
Albatrosses have locking mechanisms in the wing joints that reduce the strain on the muscles during soaring flight.
Even within a species wing morphology may differ. For example, adult European Turtle Doves have been found to have longer but more rounded wings than juveniles – suggesting that juvenile wing morphology facilitates their first migrations, while selection for flight maneuverability is more important after the juveniles' first molt.
Female birds exposed to predators during ovulation produce chicks that grow their wings faster than chicks produced by predator-free females. Their wings are also longer. Both adaptations may make them better at avoiding avian predators.


=== Wing shape ===

The shape of the wing is important in determining the flight capabilities of a bird. Different shapes correspond to different trade-offs between advantages such as speed, low energy use, and maneuverability. Two important parameters are the aspect ratio and wing loading. Aspect ratio is the ratio of wingspan to the mean of its chord (or the square of the wingspan divided by wing area). A high aspect ratio results in long narrow wings that are useful for endurance flight because they generate more lift. Wing loading is the ratio of weight to wing area.
Most kinds of bird wing can be grouped into four types, with some falling between two of these types. These types of wings are elliptical wings, high speed wings, high aspect ratio wings and slotted high-lift wings.


==== Elliptical wings ====
Technically, elliptical wings are those having elliptical (that is quarter ellipses) meeting conformally at the tips. The early model Supermarine Spitfire is an example. Some birds have vaguely elliptical wings, including the albatross wing of high aspect ratio. Although the term is convenient, it might be more precise to refer to curving taper with fairly small radius at the tips. Many small birds have a low aspect ratio with elliptical character (when spread), allowing for tight maneuvering in confined spaces such as might be found in dense vegetation. As such they are common in forest raptors (such as Accipiter hawks), and many passerines, particularly non-migratory ones (migratory species have longer wings). They are also common in species that use a rapid take off to evade predators, such as pheasants and partridges.


==== High speed wings ====
High speed wings are short, pointed wings that when combined with a heavy wing loading and rapid wingbeats provide an energetically expensive high speed. This type of flight is used by the bird with the fastest wing speed, the peregrine falcon, as well as by most of the ducks. Birds that make long migrations typically have this type of wing. The same wing shape is used by the auks for a different purpose; auks use their wings to "fly" underwater.
The peregrine falcon has the highest recorded dive speed of 242 miles per hour (389 km/h). The fastest straight, powered flight is the spine-tailed swift at 105 mph (169 km/h).


==== High aspect ratio wings ====
High aspect ratio wings, which usually have low wing loading and are far longer than they are wide, are used for slower flight. This may take the form of almost hovering (as used by kestrels, terns and nightjars) or in soaring and gliding flight, particularly the dynamic soaring used by seabirds, which takes advantage of wind speed variation at different altitudes (wind shear) above ocean waves to provide lift. Low speed flight is also important for birds that plunge-dive for fish.


==== Soaring wings with deep slots ====
These wings are favored by larger species of inland birds, such as eagles, vultures, pelicans, and storks. The slots at the end of the wings, between the primaries, reduce the induced drag and wingtip vortices by "capturing" the energy in air flowing from the lower to upper wing surface at the tips, whilst the shorter size of the wings aids in takeoff (high aspect ratio wings require a long taxi to get airborne).


== Coordinated formation flight ==

A wide variety of birds fly together in a symmetric V-shaped or a J-shaped coordinated formation, also referred to as an "echelon", especially during long-distance flight or migration. It is often assumed that birds resort to this pattern of formation flying in order to save energy and improve the aerodynamic efficiency. The birds flying at the tips and at the front would interchange positions in a timely cyclical fashion to spread flight fatigue equally among the flock members.
The wingtips of the leading bird in an echelon create a pair of opposite rotating line vortices. The vortices trailing a bird have an underwash part behind the bird, and at the same time they have an upwash on the outside, that hypothetically could aid the flight of a tr

### F05 | A wing-assisted incline running exercise regime during rearing increases initial flight velocity during descent in adult white- and brown-feathered laying hens. | https://doi.org/10.1016/j.psj.2023.103375 | cc by-nc-nd
Domestic laying hens rely primarily on their hindlimbs for terrestrial locomotion. Although they perform flapping flight, they appear to use maximal power during descent and thus may lack control for maneuvering and avoiding injuries on landing. This in turn may result in injury in open rearing systems. Wing-assisted incline running (WAIR) requires a bird to use its wings to assist the hindlimbs during climbing of an incline, and training in WAIR may therefore provide a useful method to increase a hen's power reserve and control for flight. We subjected hens to an exercise regimen involving inclines to induce WAIR for 16 wk during rearing. We then measured wing and body kinematics during aerial descent from a 155 cm platform. We hypothesized that birds reared with exercise would be better able to modulate their wing and body kinematics for making slower, more-controlled descent and landing. Brown-feathered birds exhibited greater wing beat frequencies than white-feathered birds, which is consistent with the higher wing loading of brown-feathered birds and WAIR-trained birds exhibited greater initial flight velocities compared to control birds. This may indicate that WAIR training provided an improved capacity to modulate flight velocity and strengthen the leg muscles. Providing incline exercises during rearing may therefore improve welfare for adult laying hens as greater initial flight velocity should reduce the power required for supporting body weight in the air and allow a hen to direct her excess power toward maneuvering.

### F06 | Characterization of Wing Kinematics by Decoupling Joint Movement in the Pigeon. | https://doi.org/10.3390/biomimetics9090555 | cc by
Birds have remarkable flight capabilities due to their adaptive wing morphology. However, studying live birds is time-consuming and laborious, and obtaining information about the complete wingbeat cycle is difficult. To address this issue and provide a complete dataset, we recorded comprehensive motion capture wing trajectory data from five free-flying pigeons (Columba livia). Five key motion parameters are used to quantitatively characterize wing kinematics: flapping, sweeping, twisting, folding and bending. In addition, the forelimb skeleton is mapped using an open-chain three-bar mechanism model. By systematically evaluating the relationship of joint degrees of freedom (DOFs), we configured the model as a 3-DOF shoulder, 1-DOF elbow and 2-DOF wrist. Based on the correlation analysis between wingbeat kinematics and joint movement, we found that the strongly correlated shoulder and wrist roll within the stroke plane cause wing flap and bending. There is also a strong correlation between shoulder, elbow and wrist yaw out of the stroke plane, which causes wing sweep and fold. By simplifying the wing morphing, we developed three flapping wing robots, each with different DOFs inside and outside the stroke plane. This study provides insight into the design of flapping wing robots capable of mimicking the 3D wing motion of pigeons.

### F07 | Quantitative analysis of the morphing wing mechanism of raptors: Bionic design of Falco Peregrinus wing skeleton. | https://doi.org/10.1371/journal.pone.0299982 | cc by
The wing is one of the most important parts of a bird's locomotor system and is the inspiration origination for bionic wing design. During wing motions, the wing shape is closely related to the rotation angles of wing bones. Therefore, the research on the law of bone movement in the process of wing movement can be good guidance for the design of the bionic morphing wing. In this paper, the skeletal posture of the peregrine falcon wing during the extension/flexion is studied to obtain critical data on skeletal posture. Since an elbow joint and a wrist joint rotate correlatively to drive a wing to flex/extend, the wing skeleton is simplified as a four-bar mechanism in this paper. The degree of reproduction of wing skeleton postures was quantitatively analyzed using the four-bar mechanism model, and the bionic wing skeleton was designed. It is found that the wing motions have been reproduced with high precision.

### F08 | Flapping before Flight: High Resolution, Three-Dimensional Skeletal Kinematics of Wings and Legs during Avian Development. | https://doi.org/10.1371/journal.pone.0153446 | cc by
Some of the greatest transformations in vertebrate history involve developmental and evolutionary origins of avian flight. Flight is the most power-demanding mode of locomotion, and volant adult birds have many anatomical features that presumably help meet these demands. However, juvenile birds, like the first winged dinosaurs, lack many hallmarks of advanced flight capacity. Instead of large wings they have small "protowings", and instead of robust, interlocking forelimb skeletons their limbs are more gracile and their joints less constrained. Such traits are often thought to preclude extinct theropods from powered flight, yet young birds with similarly rudimentary anatomies flap-run up slopes and even briefly fly, thereby challenging longstanding ideas on skeletal and feather function in the theropod-avian lineage. Though skeletons and feathers are the common link between extinct and extant theropods and figure prominently in discussions on flight performance (extant birds) and flight origins (extinct theropods), skeletal inter-workings are hidden from view and their functional relationship with aerodynamically active wings is not known. For the first time, we use X-ray Reconstruction of Moving Morphology to visualize skeletal movement in developing birds, and explore how development of the avian flight apparatus corresponds with ontogenetic trajectories in skeletal kinematics, aerodynamic performance, and the locomotor transition from pre-flight flapping behaviors to full flight capacity. Our findings reveal that developing chukars (Alectoris chukar) with rudimentary flight apparatuses acquire an "avian" flight stroke early in ontogeny, initially by using their wings and legs cooperatively and, as they acquire flight capacity, counteracting ontogenetic increases in aerodynamic output with greater skeletal channelization. In conjunction with previous work, juvenile birds thereby demonstrate that the initial function of developing wings is to enhance leg performance, and that aerodynamically active, flapping wings might better be viewed as adaptations or exaptations for enhancing leg performance.
