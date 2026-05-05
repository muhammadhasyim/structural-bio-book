-- Add Tufte CSS class "fullwidth" to figures that were figure* in LaTeX.
-- Label list is written by flatten_for_web.py; path is passed via PANDOC_FULLWIDTH_JSON
-- (Meta from --metadata-file is not applied before the LaTeX reader builds Figure nodes).

local json = require("pandoc.json")

function Pandoc(doc)
  local path = os.getenv("PANDOC_FULLWIDTH_JSON")
  if not path or path == "" then
    return doc
  end
  local f = io.open(path, "r")
  if not f then
    return doc
  end
  local raw = f:read("*a")
  f:close()
  local ok, data = pcall(json.decode, raw)
  if not ok or type(data) ~= "table" then
    return doc
  end
  local labels = data["fullwidth-figures"]
  if type(labels) ~= "table" then
    return doc
  end
  local idset = {}
  for _, lid in ipairs(labels) do
    if type(lid) == "string" then
      idset[lid] = true
    end
  end
  return doc:walk({
    Figure = function(fig)
      local id = fig.attr.identifier
      if id ~= "" and idset[id] then
        table.insert(fig.attr.classes, "fullwidth")
      end
      return fig
    end,
  })
end
