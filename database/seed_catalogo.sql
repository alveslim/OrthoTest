CREATE TABLE testes_catalogo (
  id          SMALLINT PRIMARY KEY,
  regiao      VARCHAR(50)  NOT NULL,
  nome        VARCHAR(100) NOT NULL UNIQUE,
  estrutura   VARCHAR(100),
  definicao   TEXT NOT NULL,
  objetivo    TEXT NOT NULL,
  como_fazer  TEXT NOT NULL,
  positivo_se TEXT NOT NULL,
  referencia  TEXT          -- fica NULL até o ORT-02 trazer a fonte verificada
);