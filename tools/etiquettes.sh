#!/bin/bash

cat <<EOF
\documentclass[a4paper]{article}
\usepackage[margin=5mm,landscape]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1,OT1]{fontenc}
\def\tagwidth{9cm}
\def\tagheight{5cm}
\newcommand{\tag}[3]{%
\fbox{\begin{minipage}[c][\tagheight]{\tagwidth}
\centering\Large
{\huge #1 #2}

\bigskip

#3

\bigskip

{\large CLA 2015}
\end{minipage}}
}
\newcommand{\passwd}[4]{%
\fbox{\begin{minipage}[c][\tagheight]{\tagwidth}
\centering
{\Large #1 #2}

\bigskip

\raggedright
\qquad{\Large login: \texttt{#3}}

\bigskip

\qquad{\Large password: \texttt{#4}}
\end{minipage}}
}

\setlength{\parindent}{0cm}
\begin{document}
\noindent
EOF
cat $1 | sed '1d;s! ,!,!g;s!, !,!g;' | awk -F',' '
{printf "\\tag{%s}{%s}{%s}%%\n", $1,$2,$3}
FNR % 3 == 0 {printf "\n"}
'
#echo '\newpage'
echo '\par'
cat $1 | sed '1d;s! ,!,!g;s!, !,!g;' | 
awk -F',' '$7 != "NON" {print $0}' |
awk -F',' '
{printf "\\passwd{%s}{%s}{%s}{%s}%%\n", $1,$2,$7,$8}
FNR % 3 == 0 {printf "\n"}
'
echo '\end{document}'
