# Recetas de objetos faltantes para el escenario (recetas_objetos/v1, formato Star)

Eres Argon. La biblioteca de formas de MYIA (283 formas) NO tiene los objetos de abajo. Tarea: para CADA objeto de la lista, escribir su receta de partes geométricas simples para Blender, con la caja, el apoyo y los colores que ya trae su ficha, y la evidencia de cada medida.

## Objetos (VARIABLE: fichas sacadas de n8n en solo lectura — 4a1 posición/utilería, 4a2 tamaños, 4b/4c y ADN del objeto; mandan sobre cualquier fuente)
Grupo: G3_utiles_dibujo
[
 {
  "objeto_id": "obj-lapiz",
  "nombre": "obj-lapiz",
  "caja_m": {
   "ancho": 0.025,
   "fondo": 0.18,
   "alto": 0.025
  },
  "colores_usados": {
   "*": "#FFC928"
  },
  "apoyo": "sobre_otro",
  "donde": [
   {
    "escenas": [
     "1",
     "2",
     "3",
     "8",
     "9"
    ],
    "junto_a": "Sobre la mesa de noche junto a obj-cama",
    "pared": null
   }
  ]
 },
 {
  "objeto_id": "amb-esc-habitacion-bote-crayones",
  "nombre": "Cubilete bajo con crayones gruesos de cera",
  "caja_m": {
   "ancho": 0.12,
   "fondo": 0.12,
   "alto": 0.11
  },
  "material_4a1": "Madera y cera mate de colores",
  "color_4a1": "Crayones rojo, azul, verde y amarillo",
  "colores_usados": {
   "*": "#B0B0B0"
  },
  "apoyo": "sobre_otro",
  "donde": [
   {
    "escenas": null,
    "junto_a": null,
    "pared": "derecha"
   }
  ]
 },
 {
  "objeto_id": "obj-pincel-magico",
  "nombre": "Pincel Mágico",
  "caja_m": {
   "ancho": 0.025,
   "fondo": 0.025,
   "alto": 0.18
  },
  "colores_usados": {
   "*": "#FFC928"
  },
  "rama_4b": {
   "forma": "cilindro",
   "medidas": "falta",
   "material": "falta",
   "cita": "Pintor dibuja en el aire con su Pincel Mágico.",
   "prompt_imagen": "3D stylized CGI magical artist paintbrush for a kid hero, colorful paint tip, neon emissive magic glow, smooth beveled handle"
  },
  "apoyo": "en_mano",
  "donde": [
   {
    "escenas": [
     "3",
     "8"
    ],
    "junto_a": "Sostenido en la mano por ch-pintor-bce0 en la zona central",
    "pared": null
   }
  ],
  "adn_texto": "1. Identificación y Geometría Base:\n\n- Pincel estilizado 3D de proporciones gruesas (estilo cartoon) y construcción rígida de una sola pieza. Silueta compuesta por una punta bulbosa en forma de gota lisa, virola cilíndrica corta, mango tubular con ligera conicidad y base semiesférica redondeada.\n- Modo de sujeción: Agarre manual directo sobre el cilindro central del mango.\n\n2. Materiales y Paleta de Color:\n\n- Chasis principal (Mango): Acabado plástico o madera satinada en color amarillo cálido, rematado en el extremo inferior por un tapón en azul real mate.\n- Materiales secundarios: Virola de metal dorado satinado con reflejos suaves; punta en estado inactivo de material sintético liso y mate en color crema/marfil.\n- Emisión lumínica: En estado activo, la punta emite luz propia con efecto *bloom* en dos variantes: degradado multicolor (naranja, cian y magenta) o amarillo neón sólido.\n\n3. Detalles Superficiales, Grabados o Componentes:\n\n- Superficie totalmente limpia, carente de grabados, botones o textura de cerdas individuales.\n- Componentes geométricos: Dos anillos toroidales en relieve situados en los bordes superior e inferior de la virola dorada, y una ranura de unión perimetral simple que divide el cuerpo amarillo del tapón azul inferior.\n\n4. Comportamiento en Escena y Escala (LOD):\n\n- Estado inactivo/activo: Inactivo se mantiene vertical y opaco; al activarse se inclina diagonalmente y la punta irradia un aura luminosa suave que proyecta reflejos de color sobre el anillo superior de la virola dorada.\n- Regla de distancia (Plano general): Se eliminan los dos rebordes de la virola y los reflejos metálicos, simplificando la silueta a cuatro bloques básicos de color (gota superior, franja dorada, cilindro amarillo, base azul).\n\n5. Prompt Compacto de Inyección (1 solo párrafo):\n\nPincel 3D estilizado de proporciones gruesas y estética cartoon minimalista, formado por una punta bulbosa en forma de gota totalmente lisa sin cerdas, virola metálica dorada con dos anillos redondeados en relieve, mango cilíndrico amarillo cálido satinado y base semiesférica en azul marino mate. En reposo la punta es de color crema opaco; en estado activo, la punta se ilumina intensamente emitiendo un halo de energía mágica difusa en degradado arcoíris (naranja, cian, fucsia) o en amarillo neón brillante."
 },
 {
  "objeto_id": "obj-papel-numeros",
  "nombre": "Papel con números del 6 al 10",
  "caja_m": {
   "ancho": 0.06,
   "fondo": 0.002,
   "alto": 0.045
  },
  "colores_usados": {
   "*": "#F2E2CE"
  },
  "rama_4b": {
   "forma": "plano",
   "medidas": "falta",
   "material": "Papel",
   "cita": "Primer plano: dice \"6, 7, 8, 9, 10\" con un dibujo de su rayo.",
   "prompt_imagen": "3D stylized CGI small sheet of paper on the floor showing numbers 6 7 8 9 10 and a doodle of a purple ray gadget"
  },
  "apoyo": "piso",
  "donde": [
   {
    "escenas": [
     "9"
    ],
    "junto_a": "Sobre el piso a los pies de ch-don-caos-7adf en el centro de la habitación",
    "pared": null
   }
  ],
  "adn_texto": "1. Identificación y Geometría Base:\n\n- Lámina o tarjeta rectangular vertical de una sola pieza flexible, con esquinas redondeadas y grosor mínimo pero perceptible (estilo cartulina 3D estilizada). Presenta dos pliegues centrales marcados en cruz (vertical y horizontal) que curvan ligeramente su perfil.\n- Modo de sujeción: Objeto de mano (sujeción con los dedos) o en reposo sobre superficies (plano, alabeado o plegado).\n\n2. Materiales y Paleta de Color:\n\n- Material principal: Papel grueso o cartulina ligeramente envejecida, acabado mate suave con bordes suavizados. Color crema / beige cálido.\n- Materiales secundarios: Trazos de crayón o lápiz de color de textura granulada y seca en la cara frontal. Color púrpura medio para los elementos principales y lila claro para detalles secundarios. Reverso del mismo material base sin pigmentos adicionales.\n- Emisión lumínica: Ninguna.\n\n3. Detalles Superficiales, Grabados o Componentes:\n\n- Centro frontal: Dibujo infantil en crayón púrpura de una pistola espacial retro-futurista apuntando en diagonal hacia arriba a la derecha (incluye aleta trasera, empuñadura con gatillo, tres anillos en el cañón y punta esférica).\n- Periferia frontal (arriba y abajo del arma): Nueve símbolos de rayos o chispas eléctricas dibujados a mano en tono lila claro.\n- Zona inferior frontal: Secuencia numérica \"6 7 8 9 10\" escrita a mano en crayón púrpura.\n- Reverso: Completamente liso y vacío, mostrando únicamente la hendidura de los pliegues en cruz.\n\n4. Comportamiento en Escena y Escala (LOD):\n\n- Estado activo/inactivo: Prop pasivo y maleable. Puede presentarse abierto (con ligera ondulación natural por el uso) o completamente doblado por sus líneas de pliegue, mostrando mayor acumulación de arrugas superficiales.\n- Regla de distancia (Plano general): A larga distancia se simplifica como una tarjeta crema con una silueta púrpura diagonal en el centro, omitiendo la textura granulada del crayón, los rayos pequeños y los números inferiores.\n\n5. Prompt Compacto de Inyección (1 solo párrafo):\n\nLámina rectangular vertical de cartulina color crema en estilo 3D estilizado, con esquinas redondeadas, grosor sutil y pliegues marcados en cruz al centro. En la cara frontal muestra un dibujo infantil hecho con crayón púrpura de una pistola láser retro apuntando hacia la esquina superior derecha, rodeada de pequeños rayos color lila y con los números \"6 7 8 9 10\" escritos a mano en el borde inferior; el reverso es completamente liso y sin dibujos. Acabado mate suave con textura de papel ligeramente arrugado."
 }
]

## Partes permitidas (formas_detalle de Star; NINGÚN otro tipo)
Partes que puede pedir la respuesta (coordenadas LOCALES del objeto: origen en el centro de su base,
x a la derecha, y hacia atrás, z arriba; luego se gira rot_z_grados y se lleva a pos_m):
  caja      {centro_m, tam_m, rot_grados?}
  tramo     {a_m, b_m, radio_m}                    cilindro entre dos puntos (patas, cables, tubos)
  cilindro  {centro_m, radio_m, alto_m, rot_grados?}
  esfera    {centro_m, radio_m}
  toro      {centro_m, radio_mayor_m, radio_menor_m, rot_grados?}
  tubo      {centro_m, radio_ext_m, radio_int_m, alto_m, segmentos?}   anillo hueco hecho de bloques
  placa     {centro_m, radio_m, espesor_m, rot_grados?}               disco fino
  cono      {a_m, b_m, radio_a_m, radio_b_m}        cono o tronco de cono entre dos puntos (radio_b_m 0 = punta)
  poliedro  {vertices_m}                            trozo convexo libre
`color_guia_rgb` = [r, g, b] entre 0 y 1. `rot_grados` = [rx, ry, rz] en grados. `nombre` en minúsculas snake_case, único dentro de la receta.

## Protocolo (en este orden)
1. Lee la ficha: `caja_m` (ancho = x, fondo = y, alto = z, en metros), `apoyo`, colores (`color_4a1`, `colores_usados`, `adn_texto`) y descripción (`nombre`, `material_4a1`, `rama_4b`, `adn_texto`).
2. Busca en el CORPUS cómo es ese tipo de objeto en la realidad: partes que lo forman y proporciones entre ellas.
3. Arma la receta: entre 3 y 25 partes (máximo 40), las suficientes para que se reconozca en plano medio. La silueta llena la caja: el conjunto de partes mide la caja en cada eje (tolerancia 1 cm o 5 %) y NINGUNA parte sale de ella.
4. Apoyo: `piso` o `sobre_otro` → lo más bajo toca z = 0. `pared` o `montado_frente` → la espalda toca y = +fondo/2. `techo` → lo más alto toca z = alto. Nada flota: todas las partes se tocan entre sí formando una sola pieza, salvo `conjunto: true` (letras o números sueltos), donde cada pieza suelta toca su apoyo.
5. Colores: SOLO los de la ficha (hex de `color_4a1`/`colores_usados` pasados a 0–1, o el color que nombra el ADN). Si la ficha no da color de una parte, usa el color principal y anótalo en `vacios`.
6. Evidencia de cada medida y proporción en `datos`.

## Reglas de evidencia (un programa sin IA las comprueba y RECHAZA la respuesta si falla una)
E1. Usa SOLO el CORPUS de abajo como fuente externa. Cada fuente tiene id (F01, F02…), título y URL.
E2. Cada dato en `datos` lleva `origen`:
    - `fuente`: `fuente_id` + `cita` = frase LITERAL de 8–300 caracteres copiada EXACTA del texto de esa fuente;
    - `hoja`: `campo_hoja` = ruta con puntos de un campo de la ficha del objeto (p. ej. `caja_m.alto`, `color_4a1`, `adn_texto`);
    - `deduccion`: `deriva_de` = claves de otros datos de la MISMA receta + `razon`.
E3. Si el corpus no trae un dato, NO lo inventes ni cites de memoria: ponlo como `deduccion` explícita o en `vacios`.
E4. La caja (`caja_m`) y el `apoyo` se copian de la ficha sin cambiarlos. No inventes URLs ni fuentes fuera del corpus. `fecha` = 2026-11-09.
E5. Responde SOLO con UN objeto JSON válido (recetas_objetos/v1), con una receta por objeto de la lista y en el mismo orden. Sin texto antes ni después, sin ``` .

## ESQUEMA recetas_objetos/v1
{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"recetas_objetos/v1","title":"Recetas de objetos faltantes en formato Star (partes de formas_detalle)","description":"Una receta por objeto. Coordenadas LOCALES en metros: origen en el centro de la base, x = ancho (derecha), y = fondo (hacia atrás), z = arriba; el FRENTE mira a −y. Todas las partes caben en la caja del objeto: x∈[−ancho/2, ancho/2], y∈[−fondo/2, fondo/2], z∈[0, alto]. Cada medida lleva evidencia (fuente + cita literal del CORPUS, hoja = campo de la ficha del objeto, o deduccion).","type":"object","additionalProperties":false,"required":["schema","grupo","fecha","recetas"],"properties":{"schema":{"const":"recetas_objetos/v1"},"grupo":{"type":"string"},"fecha":{"type":"string"},"recetas":{"type":"array","minItems":1,"items":{"type":"object","additionalProperties":false,"required":["objeto_id","nombre","caja_m","apoyo","conjunto","partes","datos","vacios"],"properties":{"objeto_id":{"type":"string"},"nombre":{"type":"string"},"caja_m":{"type":"object","additionalProperties":false,"required":["ancho","fondo","alto"],"properties":{"ancho":{"type":"number","exclusiveMinimum":0},"fondo":{"type":"number","exclusiveMinimum":0},"alto":{"type":"number","exclusiveMinimum":0}}},"apoyo":{"enum":["piso","sobre_otro","pared","techo","montado_frente","en_mano"],"description":"igual al de la ficha. piso/sobre_otro: toca z=0. pared/montado_frente: toca la cara de atrás y=+fondo/2. techo: toca z=alto. en_mano: libre"},"conjunto":{"type":"boolean","description":"true solo si el objeto son piezas sueltas (p. ej. letras o números separados); cada pieza suelta igual debe tocar su apoyo"},"partes":{"type":"array","minItems":1,"maxItems":40,"items":{"type":"object","required":["tipo","nombre","color_guia_rgb"],"properties":{"tipo":{"enum":["caja","tramo","cilindro","esfera","toro","tubo","placa","cono","poliedro"]},"nombre":{"type":"string","pattern":"^[a-z][a-z0-9_]{0,40}$"},"color_guia_rgb":{"type":"array","items":{"type":"number","minimum":0,"maximum":1},"minItems":3,"maxItems":3},"centro_m":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"tam_m":{"type":"array","items":{"type":"number","exclusiveMinimum":0},"minItems":3,"maxItems":3},"rot_grados":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"a_m":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"b_m":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"radio_m":{"type":"number","exclusiveMinimum":0},"alto_m":{"type":"number","exclusiveMinimum":0},"radio_mayor_m":{"type":"number","exclusiveMinimum":0},"radio_menor_m":{"type":"number","exclusiveMinimum":0},"radio_ext_m":{"type":"number","exclusiveMinimum":0},"radio_int_m":{"type":"number","exclusiveMinimum":0},"segmentos":{"type":"integer","minimum":6,"maximum":32},"espesor_m":{"type":"number","exclusiveMinimum":0},"radio_a_m":{"type":"number","minimum":0},"radio_b_m":{"type":"number","minimum":0},"vertices_m":{"type":"array","minItems":4,"maxItems":24,"items":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3}}}}},"datos":{"type":"array","minItems":1,"items":{"type":"object","required":["clave","valor","origen"],"properties":{"clave":{"type":"string","description":"p. ej. receta.<parte>.<medida> o proporcion.<algo>"},"valor":{},"unidad":{"type":["string","null"]},"origen":{"enum":["fuente","hoja","deduccion"]},"fuente_id":{"type":["string","null"]},"cita":{"type":["string","null"],"description":"8–300 caracteres copiados LITERAL del texto de la fuente"},"campo_hoja":{"type":["string","null"],"description":"ruta con puntos de un campo de la FICHA del objeto, p. ej. caja_m.alto, color_4a1, adn_texto"},"deriva_de":{"type":"array","items":{"type":"string"}},"razon":{"type":"string"}}}},"vacios":{"type":"array","items":{"type":"string"}}}}}}}

## Formato de una parte (ilustración de formato, NO son datos a copiar)
{"tipo":"cilindro","nombre":"cuerpo","color_guia_rgb":[0.9,0.8,0.6],"centro_m":[0,0,0.1],"radio_m":0.05,"alto_m":0.2}

## CORPUS (VARIABLE: descargado por el recolector de MYIA; archivo y sha256 en el registro de la llamada)
### F01 | Pencil | https://en.wikipedia.org/wiki/Pencil | CC BY-SA 4.0 (Wikipedia)
A pencil ( ) is a writing or drawing implement with a solid pigment core in a protective casing that reduces the risk of core breakage and keeps it from marking the user's hand.
Pencils create marks by physical abrasion, leaving a trail of solid core material that adheres to a sheet of paper or other surface. They are distinct from pens, which dispense liquid or gel ink onto the marked surface.
Most pencil cores are made of graphite powder mixed with a clay binder. Graphite pencils (traditionally known as "lead pencils") produce grey or black marks that are easily erased, but otherwise resistant to moisture, most solvents, ultraviolet radiation and natural aging. Other types of pencil cores, such as those of charcoal, are mainly used for drawing and sketching. Coloured pencils are sometimes used by teachers or editors to correct submitted texts, but are typically regarded as art supplies, especially those with cores made from wax-based binders that tend to smear when erasers are applied to them. Grease pencils have a softer, oily core that can leave marks on smooth surfaces such as glass or porcelain.
The most common pencil casing is thin wood, usually hexagonal in section, but sometimes cylindrical or triangular, permanently bonded to the core. Casings may be of other materials, such as plastic or paper. To use the pencil, the casing must be carved or peeled off to expose the working end of the core, which serves as a sharp point. Mechanical pencils have more elaborate casings which are not bonded to the core; instead, they support separate, mobile pigment cores that can be extended or retracted (usually through the casing's tip) as needed. These casings can be reloaded with new cores (usually graphite) as the previous ones are exhausted.


== History ==


=== Camel hair ===
Pencil, from Old French pincel, from late Latin penicillus a "little tail" (see penis; pincellus) originally referred to an artist's fine brush of camel hair, also used for writing before modern lead or chalk pencils.
Though the archetypal pencil was an artist's brush, the stylus, a thin metal stick used for scratching in papyrus or wax tablets, was used extensively by the Romans and for palm-leaf manuscripts.


=== Graphite deposit discoveries ===
As a technique for drawing, the closest predecessor to the pencil was silverpoint or leadpoint until, in 1565 (some sources say as early as 1500), a large deposit of graphite was discovered on the approach to Grey Knotts from the hamlet of Seathwaite in Borrowdale parish, Cumbria, England. This particular deposit of graphite was extremely pure and solid, and it could easily be sawn into sticks. It remains the only large-scale deposit of graphite ever found in this solid form. Chemistry was in its infancy, and the substance was thought to be a form of lead. Consequently, it was called plumbago (Latin for "lead ore"). Because the pencil core is still referred to as "lead", or "a lead", many people have the misconception that the graphite in the pencil is lead, and the black core of pencils is still referred to as lead, even though it never contained the element lead. The words for pencil in German (Bleistift), Irish (peann luaidhe), Arabic (قلم رصاص qalam raṣāṣ), and some other languages literally mean lead pen.
The value of graphite would soon be realised to be enormous, mainly because it could be used to line the moulds for cannonballs; the mines were taken over by the Crown and were guarded. When sufficient stores of graphite had been accumulated, the mines were flooded to prevent theft until more was required.
The usefulness of graphite for pencils was also discovered, but initially it had to be smuggled out of England. Because graphite is soft, it requires some form of encasement. Graphite sticks were initially wrapped in string or sheepskin for stability. England would enjoy a monopoly on the production of pencils until a method for reconstituting graphite powder was discovered in Germany in 1662. However, the distinctively square English pencils continued to be made with sticks cut from natural graphite into the 1860s. The town of Keswick, near the original findings of block graphite, still manufactures pencils, the factory also being the location of the Derwent Pencil Museum. The meaning of "graphite writing implement" apparently evolved late in the 16th century.


=== Wood encasement ===

Around 1560, an Italian couple, Simonio and Lyndiana Bernacotti, made what are likely the first blueprints for the modern, wood-encased carpentry pencil. Their version was a flat, oval, more compact type of pencil. Their concept involved the hollowing out of a stick of juniper wood. Shortly thereafter, a superior technique was discovered: two wooden halves were carved, a graphite stick inserted, and the halves then glued together—essentially the same method in use to this day.


=== Graphite powder and clay ===
The first attempt to manufacture graphite sticks from powdered graphite was in Nuremberg, Germany, in 1662. It used a mixture of graphite, sulphur, and antimony.
English and German pencils were not available to the French during the Napoleonic Wars; France, under a naval blockade imposed by Great Britain, was unable to import the pure graphite sticks from the British Grey Knotts mines – the only known source in the world. France was also unable to import the inferior German graphite pencil substitute. It took the efforts of an officer in Napoleon's army to change this. In 1795, Nicolas-Jacques Conté discovered a method of mixing powdered graphite with clay and forming the mixture into rods that were then fired in a kiln. By varying the ratio of graphite to clay, the hardness of the graphite rod could also be varied. This method of manufacture, which was discovered earlier by the Austrian Joseph Hardtmuth, the founder of Vienna's Koh-I-Noor company in 1790, remains in use. In 1802, the production of graphite leads from graphite and clay was patented by Koh-I-Noor.
In England

### F02 | Crayon | https://en.wikipedia.org/wiki/Crayon | CC BY-SA 4.0 (Wikipedia)
A crayon (or wax pastel) is a stick of pigmented wax used for writing or drawing. Wax crayons differ from pastels, in which the pigment is mixed with a dry binder such as gum arabic, and from oil pastels, where the binder is a mixture of wax and oil.
Crayons are available in a range of prices, and are easy to work with. They are less messy than most paints and markers, blunt (removing the risk of sharp points present when using a pencil or pen), typically non-toxic, and available in a wide variety of colors. These characteristics make them particularly good instruments for teaching small children to draw in addition to being used widely by student and professional artists.


== Composition ==
In the modern English-speaking world, the term crayon is commonly associated with the standard wax crayon, such as those widely available for use by children. Such crayons are usually approximately 3.5 inches (89 mm) in length and made mostly of paraffin wax. Paraffin wax is heated and cooled to achieve the correct temperature, at which a usable wax substance can be dyed, manufactured and then shipped for use around the world. Paraffin waxes are used for cosmetics, candles, for the preparation of printing ink, fruit preserving, in the pharmaceutical industry, for lubricating purposes, and for manufacturing crayons.
Colin Snedeker, a chemist for Binney & Smith (the then-parent company of Crayola), developed the first washable crayons in response to consumer complaints regarding stained fabrics and walls. A patent for the washable solid marking composition utilized in the washable crayons was awarded to Snedeker in 1990.


== History ==

The history of the crayon is not entirely clear. The French word crayon, originally meaning "chalk pencil", dates to around the 16th century, and is derived from the word craie (chalk), which comes from the Latin word creta (Earth). The meaning later changed to simply "pencil", which it still means in modern French.
The notion to combine a form of wax with pigment goes back thousands of years. Encaustic painting is a technique that uses hot beeswax combined with colored pigment to bind color into stone. A heat source was then used to "burn in" and fix the image in place. Pliny the Elder, a Roman scholar, was thought to describe the first techniques of wax crayon drawings.
This method, employed by the Egyptians, Romans, Greeks, and indigenous people in the Philippines, is still used today. However, the process was not used to make crayons into a form intended to be held and colored with and was therefore ineffective for use in a classroom or as crafts for children.
Contemporary crayons are purported to have originated in Europe, where some of the first cylinder shaped crayons were made with charcoal and oil. Pastels are an art medium sharing roots with the modern crayon and date back to Leonardo da Vinci in 1495. Conté crayons, out of Paris, are a hybrid between a pastel and a conventional crayon, used since the late 1790s as a drawing crayon for artists. Later, various hues of powdered pigment eventually replaced the primary charcoal ingredient found in most early 19th century products. References to crayons in literature appear as early as 1813 in Jane Austen's Pride and Prejudice. French lithographer Joseph Lemercier was also one of the inventors of the modern crayon. Through his Paris business circa 1828, he produced a variety of crayon and color related products. But even as those in Europe were discovering that substituting wax for the oil strengthened the crayon, various efforts in the United States were also developing.

The initial era of wax crayons saw several companies and products competing for the lucrative education and artist markets. The Franklin Mfg. Co, founded in 1876 in Rochester, New York, was one of the first companies to make and sell wax crayons, and in 1883 they appeared with a display of crayons at the World's Columbian Exposition that year.
Some of the earliest records of the modern paraffin wax crayon comes from Charles A. Bowley of Massachusetts, who developed wax coloring crayons in the late 1880s. Bowley had been selling various stationery items in the vicinity of Danvers and had developed clumps of colored wax designed for marking leather. With the need for more accuracy, he went back to his home and formed the wax crayons into more manageable cylinder shapes similar to that of a pencil. He packaged his crayons into decorative boxes and offered them through stationer clients he knew. The demand for his crayons soon exceeded his ability to keep up with production and he partnered with the American Crayon Company, who had been producing chalk crayons, in 1902.
Edwin Binney and C. Harold Smith had been long established in the coloring marketplace through Binney's Peekskill, New York, chemical works making lampblack by burning whale and carbon black, as well as their chalk products. In 1902, they developed and introduced the Staonal marking crayon. A year later in 1903, Edwin Binney's wife, Alice Stead Binney, coined the name Crayola by combining the French word for chalk, craie, with the first part of oleaginous, another name for the paraffin wax used to make the crayon. Binney and Smith were quick to capitalize on their creation, selling boxes of various sizes and color pallets. The Rubens Crayola line started in 1903 as well, aimed at artists and designed to compete with the Raphael brand of crayons from Europe.

Their most recognizable brand was the Crayola "Gold Medal" line in yellow boxes, which referred to one the company earned with their An-du-Septic dustless chalk during the March 1904 St. Louis World's Fair. They used the award to design a new line of crayons featuring the medal on the front of their box. Initially, they developed and introduced the No. 8 box of eight assorted colors, which became an immediate success; it was even featured on a postage stamp in early 1905. From there they began to phase out other Crayola crayon b

### F03 | Paintbrush | https://en.wikipedia.org/wiki/Paintbrush | CC BY-SA 4.0 (Wikipedia)
A paintbrush is a brush used to apply paint or ink. A paintbrush is usually made by clamping bristles to a handle with a ferrule. They are available in various sizes, shapes, and materials. Thicker ones are used for filling in, and thinner ones are used for details. They may be subdivided into decorators' brushes used for painting and decorating and artists' brushes used for visual art.


== History ==

Paintbrushes were used by humans as early as the Paleolithic era around 2.5 million years ago in order to apply pigment.
Old painting kits, estimated to be around 100,000 years old, were discovered in a cave in what is now modern South Africa.
Ancient Egyptian paintbrushes were made of split palm leaves and used by ancestors to beautify their surroundings. The oldest brushes ever found were also made of animal hair.


== Parts ==

A paintbrush consists of three main components: the bristles, the ferrule, and the handle. The bristles, which form the tuft of the brush, are responsible for transferring paint onto the surface being painted. They may be made from natural or synthetic materials, depending on the intended application. The ferrule is the metal band that holds the bristles in place and secures them to the handle. The handle serves as the interface between the user and the tool.


== Trade ==
Brushes for use in non-artistic trade painting are geared to applying an even coat of paint to relatively large areas. Following are the globally recognized handles of trade painter's brushes:

Gourd handle: Ergonomic design that reduces stress on the wrist and hand whilst painting.
Short handle: The shorter handle provides greater precision when painting small spaces such as corners, trims & detail areas.
Flat beavertail handle: This shape is rounded and slightly flattened to fit perfectly into the palm of the hand while painting.
Square handle: The square shaped handle with bevelled corners is featured mainly in trim or sash brushes and is comfortable to hold when painting.
Rat tail handle: This handle is longer & thinner than the standard, making it easy to hold to give the user greater control.
Long handle: Rounded and thin, a long handle is easy to hold like a pencil, giving great control & precision when painting complex details.


== Decorating ==

The sizes of brushes used for painting and decorating.


=== Decorating sizes ===
Decorators' brush sizes are given in millimeters (mm) or inches (in), which refers to the width of the head. Common sizes are:

Metric (mm): 10 • 20 • 40 • 50 • 60 • 70 • 80 • 90 • 100.
Customary (inches): 1⁄8 •1⁄4 • 3⁄8 • 1⁄2 • 5⁄8 • 3⁄4 • 7⁄8 • 1 • 1+1⁄4 • 1+1⁄2 • 2 • 2+1⁄2 • 3 • 3+1⁄2 • 4.


=== Decorating shapes ===
Angled: For painting edges, bristle length viewed from the wide face of the brush uniformly decrease from one end of the brush to the other
Flat: For painting flat surfaces, bristle length viewed from the wide face of the brush does not change
Tapered: Improves control, the bristle length viewed from the narrow face of the brush is longer in the center and tapers toward the edges
Striker: Large round (cylindrical) brush for exterior painting difficult areas


=== Decorating bristles ===
Bristles may be natural or synthetic. If the filaments are synthetic, they may be made of polyester, nylon or a blend of nylon and polyester.
Filaments can be hollow or solid and can be tapered or untapered. Brushes with tapered filaments give a smoother finish.
Synthetic filaments last longer than natural bristles. Natural bristles are preferred for oil-based paints and varnishes, while synthetic brushes are better for water-based paints as the bristles do not expand when wetted.
A decorator judges the quality of a brush based on several factors: filament retention, paint pickup, steadiness of paint release, brush marks, drag and precision painting. A chiseled brush permits the painter to cut into tighter corners and paint more precisely.
Brush handles may be made of wood or plastic while ferrules are metal (usually nickel-plated steel).


== Art ==
Short handled brushes are usually used for flat or slightly tilted work surfaces such as watercolor painting and ink painting, while long handled brushes are held horizontally while working on a vertical canvas such as for oil paint or acrylic paint.


=== Art shapes ===
The styles of brush tip seen most commonly are:

Round: pointed tip, long closely arranged bristles for detail.
Flat: for spreading paint quickly and evenly over a surface. They will have longer hairs than their Bright counterpart.
Bright: shorter than flats. Flat brushes with short stiff bristles, good for driving paint into the weave of a canvas in thinner paint applications, as well as thicker painting styles like impasto work.
Filbert: flat brushes with domed ends.  They allow good coverage and the ability to perform some detail work.
Fan: for blending broad areas of paint.
Angle: like the filbert, these are versatile and can be applied in both general painting application as well as some detail work.
Mop: a larger format brush with a rounded edge for broad soft paint application as well as for getting thinner glazes over existing drying layers of paint without damaging lower layers to protect the paintbrush
Rigger: round brushes with longish hairs, traditionally used for painting the rigging in pictures of ships. They are useful for fine lines and are versatile for both oils and watercolors.
Stippler and deer-foot stippler: short, stubby rounds
Liner: elongated rounds
Dagger: looks like angle with longish hairs, used for one stroke painting like painting long leaves.
Scripts: highly elongated rounds
Egbert: a filbert with extra long hair, used for oil painting

Some other styles of brush include:

Sumi: Similar in style to certain watercolor brushes, also with a generally thick wooden or metal handle and a broad soft hair brush that when wetted should form a fine tip. Also spelled Sumi-e (墨絵, Ink wash painting).
Hake (刷毛): An Asian style of brush

### F04 | Card stock | https://en.wikipedia.org/wiki/Card_stock | CC BY-SA 4.0 (Wikipedia)
Card stock, also called cover stock and pasteboard, is paper that is thicker and more durable than normal writing and printing paper, but thinner and more flexible than other forms of paperboard.


== Use ==
Card stock is often used for business cards, postcards, folders, playing cards, scrapbooking, and other applications requiring more durability than regular paper gives. The surface usually is smooth; it may be textured, metallic, or glossy. Common surface finishes include wove (smooth), laid (parallel ribbing produced by a dandy roll), felt (a textured surface), and embossed patterns such as cordwain and linen. When card stock is labeled cover stock, it often has a glossy coating on one or both sides (C1S or C2S, for "coated: one side" or "coated: two sides"); this is used especially in business cards and book covers.


== Measurements ==

The weight of cardstock ranges from 50# to 110# (about 135 to 300 g/m2).
The length and width of card stock often are stated in terms of the ISO system of paper sizes, in which specific dimensions are implied by numbers prefixed with the letter A. Card stock labeled A3, for example, measures 420 × 297 mm (16.5 × 11.7 in).


== See also ==
Construction paper
Paper density


== Notes ==


== References ==
