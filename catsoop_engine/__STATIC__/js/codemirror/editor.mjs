import {EditorView, basicSetup} from "codemirror"
import { pythonLanguage } from "@codemirror/lang-python"
import { cpp } from "@codemirror/lang-cpp"
import { LanguageSupport, indentUnit, bracketMatching } from "@codemirror/language";
import { indentMore, indentLess } from "@codemirror/commands";
import { keymap } from "@codemirror/view";

function python(){
    return new LanguageSupport(pythonLanguage);
}

const indentString = "    ";

function insertSoftTab({state, dispatch}){
  if (state.selection.ranges.some(r => !r.empty)){
      return indentMore({state, dispatch})
  }
  // math from https://discuss.codemirror.net/t/get-the-current-line-and-column-number-from-the-cursor-position/4162/2
  var currentColumn = state.selection.ranges[0].head - state.doc.lineAt(state.selection.main.head).from;
  dispatch(state.update(state.replaceSelection(" ".repeat(indentString.length - (currentColumn % indentString.length))), {scrollIntoView: true, userEvent: "input"}));
  return true;
}


//// TODO: maybe implement shift-tab?
//function deleteSoftTab({state, dispatch}){
//  if (state.selection.ranges.some(r => !r.empty)){
//      return indentLess({state, dispatch})
//  }
//  var currentColumn = state.selection.ranges[0].head - state.doc.lineAt(state.selection.main.head).from;
//  var lookBack = currentColumn % indentString.length;
//  if (lookBack === 0){
//    lookBack = indentString.length;
//  }
//  var prevChars
//  if (!/\S/.test(prevChars)){
//  }
//}

const newTabKeymap = {
    key: 'Tab',
    run: insertSoftTab,
    shift: insertSoftTab,
};

const languages = {
  python: python,
  cpp: cpp,
}

export function editorFromTextArea(textarea, language){
  language = typeof language === "undefined" ? "python" : language;
  var extensions = [
      basicSetup,
      languages[language](),
      indentUnit.of(indentString),
      keymap.of([newTabKeymap]),
      bracketMatching(),
      EditorView.updateListener.of(function(){
        textarea.value = view.state.doc.toString();
      }),
  ];
  var view = new EditorView({doc: textarea.value, extensions})
  textarea.parentNode.insertBefore(view.dom, textarea);
  textarea.style.display = "none";
  if (textarea.form) textarea.form.addEventListener("submit", () => {
    textarea.value = view.state.doc.toString();
  });
  return view;
}
