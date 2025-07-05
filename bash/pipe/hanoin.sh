#!/usr/bin/env bash

# Copyright (c) 2025 William Emerison Six

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.


n=$1
thisScript=$0

if [ "$n" -eq 1 ]; then
    ./hanoi1.sh
    exit
fi

# move a tower, sized n-1, from tower 1 to tower 2
$thisScript $((n-1)) | tr '123' '132'
# move a tower, sized 1, from tower 1 to tower 3
$thisScript 1 | tr '123' '132'
# move a tower, sized n-1, from tower 2 to tower 3
$thisScript $((n-1)) | tr '123' '213'
