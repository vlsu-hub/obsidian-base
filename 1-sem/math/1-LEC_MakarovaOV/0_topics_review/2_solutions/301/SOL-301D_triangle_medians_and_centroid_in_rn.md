---
title: SOL-301D центр тяжести треугольника и обобщение на Rn
date: 2026-11-23
tags:
  - author/the-nataraja
---

# Ответ к задаче 3.1 [D] — Центр тяжести треугольника и обобщение на $\mathbb{R}^n$

![[PST-301D_triangle_medians_and_centroid_in_rn]]

---

## Подробное решение

### Пункт а)
Пусть $A_1$ — середина стороны $BC$, так что отрезок $AA_1$ является медианой треугольника $ABC$, проведённой из вершины $A$. Поскольку $A_1$ — середина $BC$, направленные отрезки $\overrightarrow{A_1B}$ и $\overrightarrow{A_1C}$ имеют равные длины и противоположные направления, значит $\overrightarrow{A_1B} + \overrightarrow{A_1C} = \vec{0}$.

По [[LEC-301_vectors#Сложение и вычитание векторов|правилу треугольника]] разложим векторы $\overrightarrow{MB}$ и $\overrightarrow{MC}$ через промежуточную точку $A_1$:

$$
\overrightarrow{MB} = \overrightarrow{MA_1} + \overrightarrow{A_1B}, \qquad \overrightarrow{MC} = \overrightarrow{MA_1} + \overrightarrow{A_1C}.
$$

Сложим эти два равенства, пользуясь [[LEC-301_vectors#Свойства сложения векторов и их умножения на числа|коммутативностью и ассоциативностью сложения]]:

$$
\overrightarrow{MB} + \overrightarrow{MC} = 2\overrightarrow{MA_1} + (\overrightarrow{A_1B} + \overrightarrow{A_1C}) = 2\overrightarrow{MA_1} + \vec{0} = 2\overrightarrow{MA_1}.
$$

Подставим полученное выражение в данное условие $\overrightarrow{MA} + \overrightarrow{MB} + \overrightarrow{MC} = \vec{0}$:

$$
\overrightarrow{MA} + 2\overrightarrow{MA_1} = \vec{0} \implies \overrightarrow{AM} = 2\overrightarrow{MA_1},
$$

где использовано равенство $\overrightarrow{AM} = -\overrightarrow{MA}$.

Выразим весь вектор медианы $\overrightarrow{AA_1}$ по правилу треугольника:

$$
\overrightarrow{AA_1} = \overrightarrow{AM} + \overrightarrow{MA_1} = 2\overrightarrow{MA_1} + \overrightarrow{MA_1} = 3\overrightarrow{MA_1} \implies \overrightarrow{MA_1} = \frac{1}{3}\overrightarrow{AA_1}, \quad \overrightarrow{AM} = \frac{2}{3}\overrightarrow{AA_1}.
$$

Поскольку треугольник $ABC$ невырожден, вершина $A$ не совпадает с $A_1$ ($\overrightarrow{AA_1} \neq \vec{0}$). Равенства $\overrightarrow{AM} = \frac{2}{3}\overrightarrow{AA_1}$ и $\overrightarrow{MA_1} = \frac{1}{3}\overrightarrow{AA_1}$ означают, что точка $M$ лежит на отрезке $AA_1$ и делит его в отношении:

$$
\frac{AM}{MA_1} = \frac{\frac{2}{3}AA_1}{\frac{1}{3}AA_1} = \frac{2}{1}.
$$

Условие $\overrightarrow{MA} + \overrightarrow{MB} + \overrightarrow{MC} = \vec{0}$ полностью симметрично относительно вершин $A, B, C$. Повторяя то же рассуждение для середин сторон $AC$ и $AB$, получаем, что точка $M$ лежит на каждой из трёх медиан треугольника $ABC$ и делит каждую из них в отношении $2 : 1$, считая от вершины.

### Пункт б)
Зафиксируем произвольную точку пространства (или плоскости) $O$ и рассмотрим [[LEC-301_vectors#Нахождение координат вектора по координатам его конца и начала|радиус-векторы]] $\overrightarrow{OA}, \overrightarrow{OB}, \overrightarrow{OC}$ вершин треугольника и $\overrightarrow{OM}$ произвольной точки $M$. По [[LEC-301_vectors#Сложение и вычитание векторов|правилу вычитания векторов]] для любой точки $M$ верны тождества:

$$
\overrightarrow{MA} = \overrightarrow{OA} - \overrightarrow{OM}, \qquad \overrightarrow{MB} = \overrightarrow{OB} - \overrightarrow{OM}, \qquad \overrightarrow{MC} = \overrightarrow{OC} - \overrightarrow{OM}.
$$

Подставим их в условие $\overrightarrow{MA} + \overrightarrow{MB} + \overrightarrow{MC} = \vec{0}$ и выполним преобразования, опираясь на [[LEC-301_vectors#Свойства сложения векторов и их умножения на числа|свойства линейных операций]]:

$$
\begin{aligned}
\overrightarrow{MA} + \overrightarrow{MB} + \overrightarrow{MC} = \vec{0} &\iff (\overrightarrow{OA} - \overrightarrow{OM}) + (\overrightarrow{OB} - \overrightarrow{OM}) + (\overrightarrow{OC} - \overrightarrow{OM}) = \vec{0} \\
&\iff \overrightarrow{OA} + \overrightarrow{OB} + \overrightarrow{OC} - 3\overrightarrow{OM} = \vec{0} \\
&\iff 3\overrightarrow{OM} = \overrightarrow{OA} + \overrightarrow{OB} + \overrightarrow{OC} \\
&\iff \overrightarrow{OM} = \frac{1}{3}\left(\overrightarrow{OA} + \overrightarrow{OB} + \overrightarrow{OC}\right).
\end{aligned}
$$

Все переходы здесь равносильны ($\iff$). Вектор $\dfrac{1}{3}(\overrightarrow{OA} + \overrightarrow{OB} + \overrightarrow{OC})$ однозначно определён, а при отложении от фиксированной точки $O$ он задаёт **единственную** точку $M$ (причём по обратному ходу преобразований эта точка действительно удовлетворяет равенству $\overrightarrow{MA} + \overrightarrow{MB} + \overrightarrow{MC} = \vec{0}$). Значит, точка $M$ (центр тяжести треугольника) существует и единственна.

### Пункт в)
Рассмотрим $m \ge 1$ точек $A_1, A_2, \dots, A_m$ в $\mathbb{R}^n$ с радиус-векторами $\overrightarrow{OA_1}, \dots, \overrightarrow{OA_m}$ относительно начала координат $O(0, \dots, 0)$. Для любой точки $M \in \mathbb{R}^n$ имеем $\overrightarrow{MA_k} = \overrightarrow{OA_k} - \overrightarrow{OM}$ ($k = 1, \dots, m$).

Преобразуем условие $\sum_{k=1}^{m} \overrightarrow{MA_k} = \vec{0}$ с помощью свойств линейных операций:

$$
\begin{aligned}
\sum_{k=1}^{m} \overrightarrow{MA_k} = \vec{0} &\iff \sum_{k=1}^{m} \left(\overrightarrow{OA_k} - \overrightarrow{OM}\right) = \vec{0} \\
&\iff \left(\sum_{k=1}^{m} \overrightarrow{OA_k}\right) - m\overrightarrow{OM} = \vec{0} \\
&\iff m\overrightarrow{OM} = \sum_{k=1}^{m} \overrightarrow{OA_k} \\
&\iff \overrightarrow{OM} = \frac{1}{m}\sum_{k=1}^{m} \overrightarrow{OA_k} \qquad (\text{так как } m \ge 1 \neq 0).
\end{aligned}
$$

Равносильность переходов доказывает, что точка $M \in \mathbb{R}^n$ существует и определяется однозначно своим радиус-вектором $\overrightarrow{OM} = \dfrac{1}{m}\sum_{k=1}^{m} \overrightarrow{OA_k}$.

Пусть точки имеют координаты $A_k(a_{k,1}, a_{k,2}, \dots, a_{k,n})$ для $k = 1, \dots, m$, а искомая точка — $M(x_1, x_2, \dots, x_n)$. Тогда [[LEC-301_vectors#Нахождение координат вектора по координатам его конца и начала|координаты радиус-векторов]] совпадают с координатами точек, и по [[LEC-301_vectors#Сложение векторов и умножение вектора на число в координатах|правилам операций в координатах]] получаем формулу координат точки $M$ (среднее арифметическое координат точек $A_1, \dots, A_m$):

$$
x_i = \frac{a_{1,i} + a_{2,i} + \dots + a_{m,i}}{m} = \frac{1}{m}\sum_{k=1}^{m} a_{k,i}, \qquad i = 1, 2, \dots, n.
$$

---

## Ответ
* **а)** Доказано (через введение середины стороны и правило треугольника);
* **б)** Точка $M$ существует и единственна, $\overrightarrow{OM} = \dfrac{1}{3}(\overrightarrow{OA} + \overrightarrow{OB} + \overrightarrow{OC})$;
* **в)** Точка $M \in \mathbb{R}^n$ существует и единственна; её координаты равны $x_i = \dfrac{1}{m}\sum\limits_{k=1}^{m} a_{k,i}$ для каждого $i = 1, \dots, n$.