-- Map \newthought preprocessed as \textbf{<<NT>>...} to Tufte-style span.
function Strong(el)
  local first = el.content[1]
  if first and first.t == "Str" and first.text:sub(1, 6) == "<<NT>>" then
    first.text = first.text:sub(7)
    if first.text == "" then
      table.remove(el.content, 1)
    end
    if #el.content == 0 then
      return pandoc.Span({}, { class = "newthought" })
    end
    return pandoc.Span(el.content, { class = "newthought" })
  end
end
