"""
Copyright (C) 2014 David Boddie <david@boddie.org.uk>
              2016 Keyi Zhang
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os, struct

class HGTFile:

    def __init__(self, path):
    
        self.path = path
        self.parse_name()
    
    def parse_name(self):
    
        dir, file_name = os.path.split(self.path)
        stem, suffix = os.path.splitext(file_name)
        
        try:
            if len(stem) != 7:
                raise ValueError
        
            latitude = int(stem[1:3])
            longitude = int(stem[4:7])
            
            if stem[0] == "N":
                pass
            elif stem[0] == "S":
                latitude = -latitude
            else:
                raise ValueError
            
            if stem[3] == "W":
                longitude = -longitude
            elif stem[3] == "E":
                pass
            else:
                raise ValueError
        
        except ValueError:
            raise HGTError("Invalid file name for HGT file: %s" % file_name)
        
        self.latitude = latitude
        self.longitude = longitude
    
    def read(self):
    
        f = open(self.path, "rb")
        f.seek(0, 2)
        length = f.tell()
        f.seek(0, 0)
        
        if length == (1201 * 1201 * 2):
            size = 1201
        elif length == (3601 * 3601 * 2):
            size = 3601
        else:
            raise HGTError("Invalid size for HGT file '%s'" % self.path)
        
        format = ">" + ("h" * size)
        d = []
        i = 0
        while i < size:
        
            values = struct.unpack(format, f.read(size * 2))
            d.append(values)
            i += 1
        
        f.close()
        return d

