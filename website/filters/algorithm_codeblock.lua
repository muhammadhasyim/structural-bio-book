-- Mark verbatim blocks produced from algorithm2e (see flatten_for_web.py).
function CodeBlock(cb)
  local prefix = "WEB-ALGORITHM-BEGIN\n"
  if cb.text:sub(1, #prefix) == prefix then
    cb.text = cb.text:sub(#prefix + 1)
    cb.classes = cb.classes or {}
    table.insert(cb.classes, "algorithm")
  end
  return cb
end
